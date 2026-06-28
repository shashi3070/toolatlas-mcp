# Proxy Engine

The `ProxyEngine` (`proxy/engine.py`) is the core of ToolAtlas' MCP proxy layer.
It maintains the mapping between display tool names and upstream servers,
enriches tool descriptions, detects name collisions, and forwards tool calls.

## Architecture

```
                           ProxyEngine
                    ┌──────────────────────┐
                    │  _tool_to_server      │  dict[display_name → server_id]
                    │  _tool_info           │  dict[display_name → remote_tool_dict]
                    │  middleware            │  ProxyMiddleware (tracking + events)
                    └──────────────────────┘
                            │
                    ┌───────┴───────┐
                    │               │
              StorageBackend   ConnectionManager
              (DB reads)       (MCP clients)
```

Key internal data structures:

| Field | Type | Purpose |
|-------|------|---------|
| `_tool_to_server` | `dict[str, str]` | Display name → server UUID routing table |
| `_tool_info` | `dict[str, dict]` | Display name → original remote tool dict (preserves `"name"` field) |
| `middleware` | `ProxyMiddleware` | Tracks calls, records trace events, persists to DB |

## `list_tools` — Tool Listing with Collision Detection

### Normal Flow (no collisions)

```
For each linked server:
  1. Get MCPClient via ConnectionManager
  2. Call client.list_tools() → list of remote tool dicts
  3. For each remote tool:
     a. upsert_tool() in DB (server_id, original_name, description, input_schema)
     b. Check if tool is enabled at server level or proxy level
     c. Compute display_name = alias ?: original_name
     d. Enrich description with tags, domains, glossary terms
     e. Store in _tool_to_server[display_name] = server_id
     f. Store in _tool_info[display_name] = remote_tool_dict
     g. Add to tools_map[display_name] = {name, description, inputSchema}
```

### Collision Detection

When two servers expose a tool with the same display name, the second occurrence
gets a `{name} ({server_name})` suffix.

```python
# engine.py:130-134
existing_server = self._tool_to_server.get(display_name)
if existing_server is not None and existing_server != server_id:
    server_name = server.get("name", server_id[:8])
    display_name = f"{tool_name} ({server_name})"
```

Example: ServerA exposes `get_info` and ServerB also exposes `get_info`:

| Display Name | Routes To |
|-------------|-----------|
| `get_info` | ServerA |
| `get_info (ServerB)` | ServerB |

### Collision Scenarios

| Scenario | Result |
|----------|--------|
| 2 servers, same tool name, no alias | `get_info` + `get_info (ServerB)` |
| 3 servers, same tool name | `get_info` + `get_info (ServerB)` + `get_info (ServerC)` |
| Alias set on one server | `my-alias` (wins) + `get_info` (ServerA, no alias) |
| Alias set on both, same alias | `my-alias` + `my-alias (ServerB)` |
| Server already disconnected | Skipped with warning log |

### Server Unreachable

If `connection_manager.get_client()` raises, the server is skipped:

```
WARNING Skipping server 'ServerName' (unreachable)
```

If listing tools from a connected server fails, a reconnection is attempted once:

```python
# engine.py:83-96
try:
    remote_tools = await client.list_tools()
except Exception:
    await connection_manager.remove_client(server["id"])
    client = await connection_manager.get_client(server)  # reconnect
    remote_tools = await client.list_tools()
```

### Governance Pipeline

After listing, each tool passes through these filters:

1. **Server-level enabled check** — `db_tool.get("enabled", True)` (engine.py:110-111)
2. **Proxy-level enabled check** — `setting.get("enabled", True)` (engine.py:114-115)
3. **Tool selection** — If no setting exists, check if the tool is in the proxy's
   server selection list (engine.py:116-124)
4. **Display name resolution** — alias ?: original name (engine.py:126-128)
5. **Description enrichment** — Append tags, domains, glossary definitions (engine.py:139-166)

## `call_tool` — Tool Call Routing

### Flow

```
call_tool(slug, name, arguments)
  1. Get proxy by slug
  2. Get proxy servers
  3. If _tool_to_server empty, rebuild via list_tools
  4. Resolve server_id = _tool_to_server[name]
  5. Find server dict by server_id
  6. Get MCPClient for that server
  7. Get original_name from _tool_info[name]["name"]
  8. upsert_tool() with original_name (not display name!)
  9. Check tool setting (enabled/disabled)
  10. Start middleware tracking (trace_id, events)
  11. Execute on_before_tool_call plugin hooks
  12. Call upstream: client.call_tool(original_name, arguments)
  13. Execute on_after_tool_call plugin hooks
  14. Return result
```

### Display Name → Original Name Mapping

The critical distinction:

```python
# engine.py:222-223
remote_tool = self._tool_info.get(name, {})
original_name = remote_tool.get("name", name)
```

- `name` is the display name (e.g. `get_info (ServerB)` or alias)
- `original_name` is the real tool name on the upstream server (e.g. `get_info`)
- The upstream server call uses `original_name` — it never sees the alias or collision suffix
- `storage.upsert_tool()` also uses `original_name` so the DB record stays consistent

### Error Handling

| Condition | Behavior |
|-----------|----------|
| Tool not found in `_tool_to_server` | `ValueError("Tool '...' not found in proxy '...'")` |
| Server unreachable | `RuntimeError("Server '...' unreachable for proxy '...'")` |
| Tool disabled at proxy level | `PermissionError("Tool '...' is disabled in proxy '...'")` |
| Timeout (30s) | `TimeoutError("Tool '...' call timed out after 30s")` |
| Upstream call fails once | Reconnect and retry once |
| Reconnect also fails | `RuntimeError("Failed to reconnect to server '...'")` |

## Alias System

### How Alias Works

1. **Setting an alias**: `PATCH /api/proxies/{proxy_id}/tools/{tool_id}` with `{"alias": "my-name"}`
2. **Storage**: Written to `proxy_tool_settings.alias` column in DB
3. **Resolution during list_tools**:

   ```python
   # engine.py:126-128
   display_name = (
       setting.get("alias") if setting and setting.get("alias") else db_tool["name"]
   )
   ```
4. **Resolution in API response** (`GET /api/proxies/{proxy_id}/tools`):

   ```python
   # proxies.py:149-153
   name=setting.get("alias") if setting and setting.get("alias") else t.get("name", ""),
   original_name=t.get("name", ""),
   alias=setting.get("alias") if setting else None,
   ```

### Alias + Collision Interaction

- If an alias is set, the display name becomes the alias — no collision suffix is added.
- If two tools on different servers get the **same alias**, the second one gets the `(server_name)` suffix just like an unnamed collision.
- Empty alias (`""`) is treated the same as `None` — falls back to original name.

### API Contract

| Field | Always Present | Content |
|-------|:---:|---------|
| `name` | yes | Display name: alias (if set) else original name. Collision suffix appended if needed. |
| `original_name` | yes | The upstream server's actual tool name |
| `alias` | yes | The alias string, `""` if cleared, `null`/`None` if never set |
| `server_name` | yes | Human-readable server name (e.g. `"GitHub"`, `"Jira"`) |

## Middleware & Tracing

Every tool call goes through `ProxyMiddleware.track()`:

```python
# middleware.py:14-67
@asynccontextmanager
async def track(self, tool_name, proxy_id, tool_id, server_id, request_args):
    events = []
    trace_id = str(uuid4())
    # ... captures events during the call ...
    yield {"add_event": add_event, "trace_id": trace_id}
    # ... finally: record_call() to DB with all events + duration
```

Recorded events include:

| Event | When | Details |
|-------|------|---------|
| `request_received` | Start of call | Tool name, arguments |
| `proxy_lookup` | After proxy resolved | Proxy slug, name |
| `tool_resolution` | After tool→server map | Server name, enabled state |
| `server_call_start` | Before upstream call | Server name, transport |
| `server_response` | After upstream response | Result preview (first 300 chars) |
| `response_returned` | Before returning to client | Result preview |
| `call_completed` | Always (finally block) | Duration, success/failure |
