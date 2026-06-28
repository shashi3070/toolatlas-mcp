# Plugin System — Hook Execution & Flows

This document shows **exactly where** each hook fires at runtime, with
file:line references and complete sequence diagrams.

See [plugin-system.md](plugin-system.md) for the base class and hook signatures.
See [plugin-loading.md](plugin-loading.md) for registration and loading.

## Where Hooks Fire at Runtime

### Tool Listing Flow (`tools/list`)

```
Client → proxy_message(slug, session_id)          # server.py:175
  │
  ├─ 1. Plugin: on_before_cache_lookup             # server.py:217
  │     (short-circuit via execute_first)
  │     CachePlugin checks memory → Redis
  │
  ├─ 2. If plugin cache miss: check in-process cache
  │     (_tools_cache with TTL + jitter)
  │
  ├─ 3. If still miss: engine.list_tools(slug)     # calls ProxyEngine
  │     │
  │     └─ engine.list_tools():
  │          └─ Plugin: on_after_list_tools        # engine.py:174
  │
  ├─ 4. Plugin: on_after_cache_lookup              # server.py:239
  │     CachePlugin writes to memory + Redis
  │     MetricsPlugin increments cache_hits
  │
  └─ 5. Send tools to MCP client via SSE
```

References:
- `proxy/server.py:215-245` — MCP `list_tools` handler
- `proxy/engine.py:172-174` — `on_after_list_tools` fires here

### Tool Call Flow (`tools/call`)

```
Client → proxy_message(slug, session_id)          # server.py:175
  │
  ├─ 1. engine.call_tool(slug, name, arguments)   # server.py:250
  │     │
  │     └─ engine.call_tool():
  │          │
  │          ├─ Plugin: on_before_tool_call        # engine.py:251
  │          │   MetricsPlugin injects start_time
  │          │   ** Can raise to block the call **
  │          │
  │          ├─ Forward call to MCP server
  │          │
  │          └─ Plugin: on_after_tool_call         # engine.py:292
  │              MetricsPlugin: increment count, record duration
  │
  └─ 2. Send result to MCP client via SSE
```

References:
- `proxy/server.py:247-254` — MCP `call_tool` handler
- `proxy/engine.py:245-292` — `on_before_tool_call` and `on_after_tool_call` fire here

### Cache Invalidation

```python
# proxy/server.py:77-80
def invalidate_proxy_cache(slug: str):
    _tools_cache.pop(slug, None)
    asyncio.ensure_future(
        plugin_manager.execute("on_cache_invalidated", slug=slug)
    )
```

Fired from:
- `proxy/server.py:80` — direct invalidation
- `api/routes/proxies.py:38,62-64,73,96` — when proxies are created/updated/deleted/linked
- `services/registry_sync.py:138` — when tool changes are detected during sync

### Server Connection

```python
# services/connection_manager.py:55
await plugin_manager.execute("on_server_connected", server_id=server_id)
```

Fired when a new shared MCP client connection is established.

### Registry Sync

```python
# services/registry_sync.py:155-160
if result["added"]:
    await plugin_manager.execute("on_tool_added", server_id=sid, tool_names=result["added"])
if result["updated"]:
    await plugin_manager.execute("on_tool_updated", server_id=sid, tool_names=result["updated"])
if result["removed"]:
    await plugin_manager.execute("on_tool_removed", server_id=sid, tool_names=result["removed"])
```

Fired by `RegistrySyncService._sync_server()` every sync interval (default 30s).

## End-to-End Trace: Data Flow Through Every Class

Below are complete traces showing **exactly** which classes, methods, and
lines of code the data passes through. Both assume `CachePlugin` and
`MetricsPlugin` are registered.

### Tool Listing (`tools/list`)

```
 [MCP Client]                      [server.py]                      [PluginManager]                    [CachePlugin]
    |                                    |                                |                                |
    |  POST /proxy/{slug}/message        |                                |                                |
    |  {"method": "tools/list"}          |                                |                                |
    |----------------------------------->|                                |                                |
    |                                    |  proxy_message()               |                                |
    |                                    |  server.py:175                 |                                |
    |                                    |                                |                                |
    |                                    |  execute_first("on_before_"    |                                |
    |                                    |    cache_lookup", slug=slug)   |                                |
    |                                    |  server.py:217-218             |                                |
    |                                    |------------------------------->|                                |
    |                                    |                                |  execute_first():              |
    |                                    |                                |  manager.py:86-98             |
    |                                    |                                |  |                             |
    |                                    |                                |  |  Iterates plugins:          |
    |                                    |                                |  |  for plugin in _plugins:    |
    |                                    |                                |  |    method = getattr(        |
    |                                    |                                |  |      plugin, hook)          |
    |                                    |                                |  |    result = await method()  |
    |                                    |                                |  |    if result is not None:   |
    |                                    |                                |  |      return result          |
    |                                    |                                |  |                             |
    |                                    |                                |  +-> CachePlugin.             |
    |                                    |                                |     on_before_cache_lookup()  |
    |                                    |                                |------------------------------>|
    |                                    |                                |                                |
    |                                    |                                |                                |  Checks _memory dict
    |                                    |                                |                                |  (cache.py:64-66)
    |                                    |                                |  <-- (timestamp, tools) ------|
    |                                    |                                |       or None                  |
    |                                    |                                |                                |
    |                                    |  <---- (timestamp, tools) -----|                                |
    |                                    |         or None                |                                |
    |                                    |                                |                                |
    |                                    |  +-- If plugin returned cache: |                                |
    |                                    |  |   _tools_cache[slug] = it   |                                |
    |                                    |  |   server.py:220-221         |                                |
    |                                    |  |                             |                                |
    |                                    |  +-- Check _tools_cache[slug]  |                                |
    |                                    |      server.py:223-224        |                                |
    |                                    |                                |                                |
    |                                    |  +-- HIT > send cached tools   |                                |
    |                                    |  |    server.py:225-226        |                                |
    |                                    |  |                             |                                |
    |                                    |  +-- MISS > acquire engine     |                                |
    |                                    |       lock, double-check, then |                                |
    |                                    |       call engine.list_tools() |                                |
    |                                    |       server.py:229-234        |                                |
    |                                    |           |                    |                                |
    |                                    |           v                    |                                |
    |                                    |      [ProxyEngine]             |                                |
    |                                    |                                |                                |
    |                                    |      list_tools(slug)          |                                |
    |                                    |      engine.py:59-176          |                                |
    |                                    |                                |                                |
    |                                    |      1. Get proxy + servers    |                                |
    |                                    |         engine.py:60-64        |                                |
    |                                    |         [StorageBackend]       |                                |
    |                                    |                                |                                |
    |                                    |      2. For each server:       |                                |
    |                                    |         get_client(server)     |                                |
    |                                    |         engine.py:75           |                                |
    |                                    |         [ConnectionManager]    |                                |
    |                                    |                                |                                |
    |                                    |         client.list_tools()    |                                |
    |                                    |         engine.py:81           |                                |
    |                                    |         [MCPClient]            |                                |
    |                                    |           (SSE/stdio/http)     |                                |
    |                                    |                                |                                |
    |                                    |      3. For each tool:         |                                |
    |                                    |         upsert_tool()          |                                |
    |                                    |         engine.py:103-109      |                                |
    |                                    |         [StorageBackend]       |                                |
    |                                    |                                |                                |
    |                                    |         Check enabled +        |                                |
    |                                    |         tool_setting           |                                |
    |                                    |         engine.py:111-116      |                                |
    |                                    |                                |                                |
    |                                    |         Build enriched         |                                |
    |                                    |         display_name/desc      |                                |
    |                                    |         engine.py:127-163      |                                |
    |                                    |           (tags, domains,      |                                |
    |                                    |            glossary terms)     |                                |
    |                                    |                                |                                |
    |                                    |      4. engine.py:170          |                                |
    |                                    |         tools = list(          |                                |
    |                                    |           tools_map.values())  |                                |
    |                                    |                                |                                |
    |                                    |      5. Execute plugin hooks   |                                |
    |                                    |         engine.py:173-174      |                                |
    |                                    |                                |                                |
    |                                    |         PluginContext(          |                                |
    |                                    |           slug, "list_tools")  |                                |
    |                                    |         execute("on_after_"    |                                |
    |                                    |           list_tools",         |                                |
    |                                    |           ctx=ctx, tools=tools)|                                |
    |                                    |         |                      |                                |
    |                                    |         v                      |                                |
    |                                    |      [PluginManager]           |                                |
    |                                    |      manager.py:72-84          |                                |
    |                                    |         |                      |                                |
    |                                    |         +- MetricsPlugin.      |                                |
    |                                    |         |  after_list_tools()  |                                |
    |                                    |         |  (records tool count)|                                |
    |                                    |         |                      |                                |
    |                                    |         +- (any other plugin)  |                                |
    |                                    |                                |                                |
    |                                    |  +-- Return tools              |                                |
    |                                    |  |   engine.py:176             |                                |
    |                                    |  |        |                    |                                |
    |                                    |  |        v                    |                                |
    |                                    |  +-- Store in _tools_cache     |                                |
    |                                    |       server.py:232-234        |                                |
    |                                    |                                |                                |
    |                                    |       execute("on_after_"      |                                |
    |                                    |         cache_lookup",         |                                |
    |                                    |         slug, tools)           |                                |
    |                                    |       server.py:239            |                                |
    |                                    |------------------------------->|                                |
    |                                    |                                |                                |
    |                                    |                                |  execute():                    |
    |                                    |                                |  manager.py:72-84             |
    |                                    |                                |  |                             |
    |                                    |                                |  +- CachePlugin.               |
    |                                    |                                |     on_after_cache_lookup()   |
    |                                    |                                |------------------------------>|
    |                                    |                                |                                |
    |                                    |                                |                                |  Write to _memory + Redis
    |                                    |                                |                                |  cache.py:78-87
    |                                    |                                |                                |
    |                                    |  Send SSE event with           |                                |
    |                                    |  {"tools": [...]}              |                                |
    |                                    |  server.py:241-244             |                                |
    |                                    |                                |                                |
    |  <----- SSE: message --------------|                                |                                |
```

### Tool Call (`tools/call`)

```
 [MCP Client]                      [server.py]                      [PluginManager]                 [MetricsPlugin]
    |                                    |                                |                                |
    |  POST /proxy/{slug}/message        |                                |                                |
    |  {"method": "tools/call",          |                                |                                |
    |   "params": {"name":"x",           |                                |                                |
    |              "args":{...}}}        |                                |                                |
    |----------------------------------->|                                |                                |
    |                                    |  proxy_message()               |                                |
    |                                    |  server.py:175                 |                                |
    |                                    |                                |                                |
    |                                    |  engine.call_tool(             |                                |
    |                                    |    slug, name, arguments)      |                                |
    |                                    |  server.py:250                 |                                |
    |                                    |                                |                                |
    |                                    |  [ProxyEngine.call_tool()]     |                                |
    |                                    |  engine.py:182-294             |                                |
    |                                    |                                |                                |
    |                                    |  1. Get proxy + servers        |                                |
    |                                    |     engine.py:185-189          |                                |
    |                                    |     [StorageBackend]            |                                |
    |                                    |                                |                                |
    |                                    |  2. If _tool_to_server empty,  |                                |
    |                                    |     rebuild via list_tools     |                                |
    |                                    |     engine.py:191-197          |                                |
    |                                    |                                |                                |
    |                                    |  3. Resolve tool > server_id   |                                |
    |                                    |     engine.py:199-204          |                                |
    |                                    |                                |                                |
    |                                    |  4. Get MCPClient              |                                |
    |                                    |     engine.py:207              |                                |
    |                                    |     [ConnectionManager]         |                                |
    |                                    |                                |                                |
    |                                    |  5. Upsert tool + get setting  |                                |
    |                                    |     engine.py:214-221          |                                |
    |                                    |     [StorageBackend]            |                                |
    |                                    |                                |                                |
    |                                    |  6. Middleware tracking        |                                |
    |                                    |     engine.py:223-229          |                                |
    |                                    |     [ProxyMiddleware]           |                                |
    |                                    |     |                          |                                |
    |                                    |     +- add_event("proxy_"      |                                |
    |                                    |     |   lookup", ...)           |                                |
    |                                    |     |   engine.py:230          |                                |
    |                                    |     +- add_event("tool_"       |                                |
    |                                    |     |   resolution", ...)       |                                |
    |                                    |     |   engine.py:233          |                                |
    |                                    |     +- Check if tool is        |                                |
    |                                    |        disabled > raise         |                                |
    |                                    |        PermissionError          |                                |
    |                                    |        engine.py:238-243       |                                |
    |                                    |                                |                                |
    |                                    |  7. Execute plugin hook        |                                |
    |                                    |     engine.py:245-251          |                                |
    |                                    |                                |                                |
    |                                    |     PluginContext(              |                                |
    |                                    |       slug, "call_tool",       |                                |
    |                                    |       tool_name, arguments,    |                                |
    |                                    |       server_id)               |                                |
    |                                    |     execute("on_before_"       |                                |
    |                                    |       tool_call", ctx=pctx)    |                                |
    |                                    |------------------------------->|                                |
    |                                    |                                |  execute():                    |
    |                                    |                                |  manager.py:72-84             |
    |                                    |                                |  |                             |
    |                                    |                                |  +- MetricsPlugin.            |
    |                                    |                                |  |  on_before_tool_call()     |
    |                                    |                                |  |  metrics.py:354-355        |
    |                                    |                                |  |  +- ctx.extra[             |
    |                                    |                                |  |     "start_time"] = time() |
    |                                    |                                |  |                             |
    |                                    |                                |  +- AuditLoggerPlugin.       |
    |                                    |                                |  |  on_before_tool_call()     |
    |                                    |                                |  |  +- log.info(...)          |
    |                                    |                                |  |                             |
    |                                    |                                |  +- (any other plugin)       |
    |                                    |                                |                                |
    |                                    |  8. Forward to MCP server      |                                |
    |                                    |     engine.py:257-259          |                                |
    |                                    |     client.call_tool(           |                                |
    |                                    |       name, arguments)          |                                |
    |                                    |     +-- Timeout after 30s       |                                |
    |                                    |     |   engine.py:258-266       |                                |
    |                                    |     |   > TimeoutError           |                                |
    |                                    |     +-- On failure > reconnect  |                                |
    |                                    |         engine.py:267-281       |                                |
    |                                    |                                |                                |
    |                                    |  9. Middleware events          |                                |
    |                                    |     engine.py:283-288          |                                |
    |                                    |     +- add_event("server_"     |                                |
    |                                    |     |   response", ...)         |                                |
    |                                    |     +- add_event("response_"   |                                |
    |                                    |        returned", ...)          |                                |
    |                                    |                                |                                |
    |                                    | 10. Execute plugin hook        |                                |
    |                                    |     engine.py:290-292          |                                |
    |                                    |                                |                                |
    |                                    |     pctx.extra["duration_ms"]  |                                |
    |                                    |       = elapsed * 1000         |                                |
    |                                    |     execute("on_after_"        |                                |
    |                                    |       tool_call",             |                                |
    |                                    |       ctx=pctx, result=result) |                                |
    |                                    |------------------------------->|                                |
    |                                    |                                |  execute():                    |
    |                                    |                                |  manager.py:72-84             |
    |                                    |                                |  |                             |
    |                                    |                                |  +- MetricsPlugin.            |
    |                                    |                                |  |  on_after_tool_call()      |
    |                                    |                                |  |  metrics.py:357-361        |
    |                                    |                                |  |  +- _call_count[tool]++    |
    |                                    |                                |  |  +- _durations[tool].      |
    |                                    |                                |  |       append(dur)           |
    |                                    |                                |  |                             |
    |                                    |                                |  +- AuditLoggerPlugin.       |
    |                                    |                                |  |  on_after_tool_call()      |
    |                                    |                                |  |  +- write audit.log        |
    |                                    |                                |  |                             |
    |                                    |                                |  +- (any other plugin)       |
    |                                    |                                |                                |
    |                                    | 11. Send SSE event             |                                |
    |                                    |     server.py:251-254          |                                |
    |                                    |     {"result": {...}}          |                                |
    |                                    |                                |                                |
    |  <----- SSE: message --------------|                                |                                |
```

### Cache Invalidation Flow (triggered by registry sync)

```
[RegistrySyncService]           [ConnectionManager]           [PluginManager]               [CachePlugin]
     │                               │                               │                               │
     │  _sync_loop()                 │                               │                               │
     │  registry_sync.py:61          │                               │                               │
     │                               │                               │                               │
     │  For each server:             │                               │                               │
     │  cm.get_client(server)        │                               │                               │
     │──────────────────────────────>│                               │                               │
     │                               │  get_client(server)           │                               │
     │                               │  connection_manager.py        │                               │
     │  <──── MCPClient ─────────────│                               │                               │
     │                               │                               │                               │
     │  client.list_tools()          │                               │                               │
     │  registry_sync.py:90          │                               │                               │
     │                               │                               │                               │
     │  _compute_tool_hash()         │                               │                               │
     │  registry_sync.py:17-21       │                               │                               │
     │                               │                               │                               │
     │  ┌─ Hash unchanged → skip     │                               │                               │
     │  │  registry_sync.py:98-100   │                               │                               │
     │  │                             │                               │                               │
     │  └─ Hash changed:             │                               │                               │
     │     upsert/delete tools       │                               │                               │
     │     registry_sync.py:107-126  │                               │                               │
     │     [StorageBackend]           │                               │                               │
     │                               │                               │                               │
     │     invalidate_proxies_for_   │                               │                               │
     │     server(server["id"])      │                               │                               │
     │     registry_sync.py:137-138  │                               │                               │
     │     [server.py:87-100]        │                               │                               │
     │       │                       │                               │                               │
     │       │  For each proxy       │                               │                               │
     │       │  linked to server:    │                               │                               │
     │       │  _tools_cache.pop()   │                               │                               │
     │       │                       │                               │                               │
     │       │  plugin_manager.      │                               │                               │
     │       │  execute("on_cache_   │                               │                               │
     │       │    invalidated",      │                               │                               │
     │       │    slug=proxy_slug)   │                               │                               │
     │       │───────────────────────│                               │                               │
     │       ▼                       │                               │                               │
     │                               │                               │  execute():                    │
     │                               │                               │  manager.py:72-84             │
     │                               │                               │  │                             │
     │                               │                               │  └─ CachePlugin.              │
     │                               │                               │     on_cache_invalidated()    │
     │                               │                               │──────────────────────────────>│
     │                               │                               │                               │
     │                               │                               │                               │  _memory.pop(key)
     │                               │                               │                               │  cache.py:91
     │                               │                               │                               │  Redis delete
     │                               │                               │                               │  cache.py:93-95
     │                               │                               │                               │
     │     Plugin hooks for          │                               │                               │
     │     tool changes:             │                               │                               │
     │                               │                               │                               │
     │     execute("on_tool_added",  │                               │                               │
     │       server_id, tool_names)  │                               │                               │
     │     registry_sync.py:156      │                               │                               │
     │──────────────────────────────>│                               │                               │
     │                               │                               │  └─ (any plugin listening)    │
     │                               │                               │                               │
     │     execute("on_tool_updated",│                               │                               │
     │       server_id, tool_names)  │                               │                               │
     │     registry_sync.py:158      │                               │                               │
     │──────────────────────────────>│                               │                               │
     │                               │                               │  └─ (any plugin listening)    │
     │                               │                               │                               │
     │     execute("on_tool_removed",│                               │                               │
     │       server_id, tool_names)  │                               │                               │
     │     registry_sync.py:160      │                               │                               │
     │──────────────────────────────>│                               │                               │
     │                               │                               │  └─ (any plugin listening)    │
```

### Key Observations

| Aspect | Where It Happens |
|--------|-----------------|
| **Client entry point** | `server.py:175` — `proxy_message()` receives JSON-RPC over HTTP POST |
| **Cache short-circuit** | `server.py:217-221` — plugin can return cached data before engine runs |
| **Per-slug TTL cache** | `server.py:32-47` — in-memory `_tools_cache` with 60s TTL + jitter |
| **Plugin dispatch** | `manager.py:72-84` — `execute()` iterates `_plugins`, calls each hook |
| **Tool enrichment** | `engine.py:127-163` — tags, domains, glossary appended to description |
| **Tool→server map** | `engine.py:99-100` — built during `list_tools` on each server |
| **Before-call guard** | `engine.py:251` — plugins can raise to abort the call |
| **After-call logging** | `engine.py:292` — plugins see result + duration |
| **Background sync** | `registry_sync.py:61-73` — every 30s, hash-based change detection |
| **Error isolation** | `manager.py:82-83` — per-plugin exceptions logged, not propagated |
