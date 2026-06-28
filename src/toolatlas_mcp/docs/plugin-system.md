# Plugin System — Core Reference

## What Is a Plugin System?

A plugin system lets you add custom behavior to ToolAtlas **without modifying core code**.
You write a class that inherits from `Plugin`, override the hook methods you care about,
and drop it into the application. The plugin manager dispatches lifecycle events at
runtime — every plugin gets a chance to observe, modify, or short-circuit the flow.

## Architecture Overview

```
                     ┌─────────────────────────┐
                     │     ProxyEngine          │
                     │  (tool calls / listing)   │
                     └──────────┬──────────────┘
                                │
                    plugin_manager.execute("hook_name", **kwargs)
                                │
                    ┌───────────┼─────────────┐
                    │           │              │
                    ▼           ▼              ▼
               CachePlugin  MetricsPlugin  CustomPlugin
               (built-in)   (built-in)     (yours)
```

### Core Files

| File | Purpose |
|------|---------|
| `src/toolatlas_mcp/plugin/base.py` | `Plugin` base class + `PluginContext` dataclass |
| `src/toolatlas_mcp/plugin/manager.py` | `PluginManager` — registers plugins, dispatches hooks |
| `src/toolatlas_mcp/plugin/builtins/cache.py` | Built-in two-tier cache (memory → Redis) |
| `src/toolatlas_mcp/plugin/builtins/metrics.py` | Built-in Prometheus-style metrics collector |
| `src/toolatlas_mcp/plugin/__init__.py` | Public API exports |
| `src/toolatlas_mcp/config.py` | Settings with `plugins` and `plugin_dirs` fields |

### Related Documents

- [plugin-loading.md](plugin-loading.md) — PluginManager API, loading paths, registration
- [plugin-hooks.md](plugin-hooks.md) — Where hooks fire, execution flows, sequence diagrams
- [plugin-examples.md](plugin-examples.md) — Complete plugin examples, real-world scenarios, corner cases
- [plugin-testing.md](plugin-testing.md) — Testing patterns, mocking, error isolation

## The `Plugin` Base Class

Every plugin inherits from the `Plugin` class. All hooks are **optional async methods**
— you only override what you need.

```python
# src/toolatlas_mcp/plugin/base.py

class Plugin:
    name: str = ""  # Unique identifier, e.g. "cache", "metrics"

    # ── Lifecycle ──────────────────────────────────────────────
    async def startup(self): ...
    async def shutdown(self): ...

    # ── Tool listing ───────────────────────────────────────────
    async def on_before_list_tools(self, ctx: PluginContext) -> list[dict] | None: ...
    async def on_after_list_tools(self, ctx: PluginContext, tools: list[dict]) -> None: ...

    # ── Tool call ──────────────────────────────────────────────
    async def on_before_tool_call(self, ctx: PluginContext) -> None: ...
    async def on_after_tool_call(self, ctx: PluginContext, result: dict) -> None: ...

    # ── Server lifecycle ───────────────────────────────────────
    async def on_server_connected(self, server_id: str) -> None: ...
    async def on_server_disconnected(self, server_id: str) -> None: ...

    # ── Tool registry sync ─────────────────────────────────────
    async def on_tool_added(self, server_id: str, tool_names: list[str]) -> None: ...
    async def on_tool_updated(self, server_id: str, tool_names: list[str]) -> None: ...
    async def on_tool_removed(self, server_id: str, tool_names: list[str]) -> None: ...

    # ── Cache ──────────────────────────────────────────────────
    async def on_before_cache_lookup(self, slug: str) -> tuple[float, list] | None: ...
    async def on_after_cache_lookup(self, slug: str, tools: list) -> None: ...
    async def on_cache_invalidated(self, slug: str) -> None: ...
```

### `PluginContext` — Runtime Data Bag

```python
# src/toolatlas_mcp/plugin/base.py
@dataclass
class PluginContext:
    slug: str = ""           # Which proxy (e.g. "dev")
    method: str = ""          # "list_tools" or "call_tool"
    tool_name: str = ""       # e.g. "search_issues"
    arguments: dict = ...     # The user's tool arguments
    server_id: str = ""       # The MCP server handling the request
    extra: dict = ...         # Catch-all for custom metadata
```

`extra` is the extension point: plugins inject values into it (e.g. start time) and
other hooks (or the same plugin) read them later.

## Hook Summary Table

| Hook | Category | Short-circuit? | Fired From | File:Ln |
|------|----------|:---:|------------|:-------:|
| `startup` | Lifecycle | — | `register()` | `manager.py:27` |
| `shutdown` | Lifecycle | — | `shutdown_all()` | `manager.py:120` |
| `on_before_list_tools` | Tool listing | ✅ yes | *(not yet wired)* | — |
| `on_after_list_tools` | Tool listing | — | `ProxyEngine.list_tools()` | `engine.py:174` |
| `on_before_tool_call` | Tool call | raise to block | `ProxyEngine.call_tool()` | `engine.py:251` |
| `on_after_tool_call` | Tool call | — | `ProxyEngine.call_tool()` | `engine.py:292` |
| `on_before_cache_lookup` | Cache | ✅ yes | `proxy_message()` | `server.py:217` |
| `on_after_cache_lookup` | Cache | — | `proxy_message()` | `server.py:239` |
| `on_cache_invalidated` | Cache | — | `invalidate_proxy_cache()` | `server.py:80` |
| `on_server_connected` | Server | — | `ConnectionManager.get_client()` | `connection_manager.py:55` |
| `on_server_disconnected` | Server | — | *(not yet wired)* | — |
| `on_tool_added` | Registry | — | `RegistrySyncService._sync_server()` | `registry_sync.py:156` |
| `on_tool_updated` | Registry | — | `RegistrySyncService._sync_server()` | `registry_sync.py:158` |
| `on_tool_removed` | Registry | — | `RegistrySyncService._sync_server()` | `registry_sync.py:160` |

## Hook Arguments Reference

Every plugin hook receives specific arguments. This section documents every
parameter for every hook — its type, what data it carries, and which class
and line of code dispatches it.

### Lifecycle Hooks

| Hook | Arguments | Dispatched By |
|------|-----------|---------------|
| `startup()` | *(none)* | `PluginManager.register()` — `manager.py:29` |
| `shutdown()` | *(none)* | `PluginManager.shutdown_all()` — `manager.py:107` |

### Tool Listing Hooks

| Hook | Arguments | Dispatched By |
|------|-----------|---------------|
| `on_before_list_tools(ctx)` | `ctx.slug` — proxy slug identifying the client<br>`ctx.method` — always `"list_tools"`<br>`ctx.tool_name` — empty string<br>`ctx.arguments` — empty dict<br>`ctx.server_id` — empty string<br>`ctx.extra` — empty dict | `proxy_message()` — `server.py:217` |
| `on_after_list_tools(ctx, tools)` | `ctx.slug` — proxy slug<br>`ctx.method` — `"list_tools"`<br>`tools` — `list[dict]` of enriched tool objects, each with `name`, `description`, `inputSchema` | `ProxyEngine.list_tools()` — `engine.py:174` |

### Tool Call Hooks

| Hook | Arguments | Dispatched By |
|------|-----------|---------------|
| `on_before_tool_call(ctx)` | `ctx.slug` — proxy slug<br>`ctx.method` — `"call_tool"`<br>`ctx.tool_name` — name of the tool being called<br>`ctx.arguments` — `dict[str, Any]` of the actual invocation arguments<br>`ctx.server_id` — resolved upstream server ID<br>`ctx.extra` — mutable dict; plugins can inject values here (e.g. `start_time`) | `ProxyEngine.call_tool()` — `engine.py:251` |
| `on_after_tool_call(ctx, result)` | `ctx` — same object from `on_before_tool_call`, with `ctx.extra` potentially populated (e.g. `duration_ms` set at `engine.py:291`)<br>`result` — `dict` returned by the upstream MCP server via `client.call_tool()` | `ProxyEngine.call_tool()` — `engine.py:292` |

### Server Lifecycle Hooks

| Hook | Arguments | Dispatched By |
|------|-----------|---------------|
| `on_server_connected(server_id)` | `server_id` — `str` UUID of the server that was connected | `ConnectionManager.get_client()` — `connection_manager.py:55` |
| `on_server_disconnected(server_id)` | `server_id` — `str` UUID of the server that was disconnected | *(not yet wired)* — `connection_manager.py` |

### Registry Sync Hooks

| Hook | Arguments | Dispatched By |
|------|-----------|---------------|
| `on_tool_added(server_id, tool_names)` | `server_id` — `str` UUID of the server<br>`tool_names` — `list[str]` of tool names that appeared since last sync | `RegistrySyncService._sync_server()` — `registry_sync.py:156` |
| `on_tool_updated(server_id, tool_names)` | `server_id` — `str` UUID of the server<br>`tool_names` — `list[str]` of tool names whose definition changed | `RegistrySyncService._sync_server()` — `registry_sync.py:158` |
| `on_tool_removed(server_id, tool_names)` | `server_id` — `str` UUID of the server<br>`tool_names` — `list[str]` of tool names that no longer exist on the server | `RegistrySyncService._sync_server()` — `registry_sync.py:160` |

### Cache Hooks

| Hook | Arguments | Dispatched By |
|------|-----------|---------------|
| `on_before_cache_lookup(slug)` | `slug` — `str` proxy slug to look up in cache<br>**Returns:** `tuple[float, list] \| None` — cached `(timestamp, tools)` pair to short-circuit, or `None` to continue | `proxy_message()` — `server.py:217-218` |
| `on_after_cache_lookup(slug, tools)` | `slug` — `str` proxy slug<br>`tools` — `list` of tool dicts that were returned from cache or freshly fetched | `proxy_message()` — `server.py:239` |
| `on_cache_invalidated(slug)` | `slug` — `str` proxy slug whose cache was cleared | `invalidate_proxy_cache()` — `server.py:80` |

### PluginContext Breakdown

The `PluginContext` dataclass (`base.py:8-16`) is the primary data carrier for
tool listing and call hooks:

```python
@dataclass
class PluginContext:
    slug: str                     # proxy slug that identifies the session
    method: str                   # "list_tools" or "call_tool"
    tool_name: str                # name of the tool being invoked (empty for list_tools)
    arguments: dict[str, Any]     # invocation arguments passed by the MCP client
    server_id: str                # resolved upstream server UUID
    extra: dict[str, Any]         # mutable scratchpad -- plugins share data here
```
