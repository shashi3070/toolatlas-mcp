# Plugin System — Loading & Registration

This document covers the `PluginManager` API, the three ways to load plugins,
and how to wire them into a real ToolAtlas instance.

See [plugin-system.md](plugin-system.md) for the base class, hook signatures, and argument reference.

## The `PluginManager` — Orchestrator

The `PluginManager` singleton at `plugin/manager.py:147` stores all registered plugins
and exposes three execution strategies:

### `execute("hook", **kwargs)` — Fan-out (observers)

Calls the hook on **every** registered plugin and collects results. If a plugin raises,
the error is logged but **other plugins still run**. Returns a list of results.

```python
# src/toolatlas_mcp/proxy/engine.py:174
await plugin_manager.execute("on_after_list_tools", ctx=ctx, tools=tools)
# → CachePlugin.on_after_list_tools(ctx, tools) runs
# → MetricsPlugin.on_after_list_tools(ctx, tools) runs
# → Any other registered plugin runs
```

### `execute_first("hook", **kwargs)` — Short-circuit

Iterates plugins and returns the **first non-None result**, skipping the rest.
Used for cache lookups and early returns.

```python
# src/toolatlas_mcp/proxy/server.py:217-219
plugin_cache = await plugin_manager.execute_first(
    "on_before_cache_lookup", slug=slug,
)
if plugin_cache is not None:
    _tools_cache[slug] = plugin_cache  # Use cached data, skip normal flow
```

### `register(plugin)` — Registration

Calls `plugin.startup()` and appends to the internal list.

```python
# src/toolatlas_mcp/plugin/manager.py:25-28
await plugin_manager.register(CachePlugin())
```

### Error Isolation

```python
# src/toolatlas_mcp/plugin/manager.py:81-89
for plugin in self._plugins:
    try:
        result = await method(**kwargs)
        results.append(result)
    except Exception as e:
        log.error("Plugin %s hook %s error: %s", ...)
        # ERROR IS LOGGED BUT EXECUTION CONTINUES
```

A broken plugin never crashes the app.

## Loading Plugins

Three paths exist:

### Path 1: `register()` — Direct (for tests)

```python
# tests/test_plugin.py
plugin = SimplePlugin()
await plugin_manager.register(plugin)
assert plugin in plugin_manager.plugins
```

### Path 2: `load_from_entry_point()` — Dotted module path

```python
# src/toolatlas_mcp/plugin/manager.py:35-50
await plugin_manager.load_from_entry_point("toolatlas_mcp.plugin.builtins.cache")
```

This uses `importlib.import_module` and looks for either:
- A module-level `plugin` attribute holding a Plugin instance, **or**
- A class matching the last segment of the dotted path

The built-in plugins export a `plugin` instance at module level:
```python
# src/toolatlas_mcp/plugin/builtins/cache.py:139
plugin = CachePlugin()
```

### Path 3: `discover()` — Scan directories

```python
# src/toolatlas_mcp/plugin/manager.py:58-63
await plugin_manager.discover([Path("/etc/toolatlas/plugins")])
```

Finds `plugin.py` files in subdirectories and calls `load_from_entry_point` on each.

### Configuration (planned wiring)

The `Settings` class has two fields ready for use:
```python
# src/toolatlas_mcp/config.py
class Settings(BaseSettings):
    plugins: list[str] = []       # TOOLATLAS_PLUGINS env var
    plugin_dirs: list[str] = []   # TOOLATLAS_PLUGIN_DIRS env var
```

The actual startup loop (iterating these and calling `load_from_entry_point` /
`discover`) is **not yet wired** in `api/app.py` or `cli/main.py`. Once wired,
plugins would be loaded during the FastAPI `startup` event.

## Using a Custom Plugin in the Application

### Option A: Wire It at App Startup (Recommended)

Add plugin registration to the FastAPI `startup` event in `api/app.py`:

```python
# api/app.py — within the startup() function
from toolatlas_mcp.plugin import plugin_manager
from my_audit_plugin.plugin import plugin as audit_plugin

@app.on_event("startup")
async def startup():
    # ... existing startup code ...

    # Register custom plugins
    await plugin_manager.register(audit_plugin)
    # For multiple:
    # await plugin_manager.load_from_entry_point("my_audit_plugin.plugin.AuditLoggerPlugin")
```

### Option B: Using the Config-Driven Approach (Planned)

The `Settings` class already has the fields ready. When the startup wiring is
implemented, loading becomes entirely config-driven:

```bash
# .env or environment variables
TOOLATLAS_PLUGINS=my_audit_plugin.plugin.AuditLoggerPlugin
# Multiple plugins:
# TOOLATLAS_PLUGINS=cache,metrics,my_audit_plugin.plugin.AuditLoggerPlugin
# Or scan a directory for plugin.py files:
# TOOLATLAS_PLUGIN_DIRS=/etc/toolatlas/plugins
```

The planned startup loop would look like:

```python
# Inside create_app() startup event
for entry_point in settings.plugins:
    await plugin_manager.load_from_entry_point(entry_point)

for plugin_dir in settings.plugin_dirs:
    await plugin_manager.discover([Path(plugin_dir)])
```

### Option C: Manual Registration in a Startup Script

For development or one-off setups, create a small script:

```python
# register_plugins.py
import asyncio
from toolatlas_mcp.plugin import plugin_manager
from my_audit_plugin.plugin import AuditLoggerPlugin


async def main():
    await plugin_manager.register(AuditLoggerPlugin())
    print(f"Registered plugins: {[p.name for p in plugin_manager.plugins]}")

    # Verify hooks work
    from toolatlas_mcp.plugin.base import PluginContext
    ctx = PluginContext(slug="dev", method="call_tool", tool_name="search_issues")
    await plugin_manager.execute("on_before_tool_call", ctx=ctx)
    print("Hooks executed successfully")


asyncio.run(main())
```

### Project Directory Structure

```
my_audit_plugin/
├── __init__.py          # (optional, empty is fine)
└── plugin.py            # Contains AuditLoggerPlugin + plugin = AuditLoggerPlugin()
```

The `plugin.py` file must expose a module-level `plugin` attribute that is a
`Plugin` instance. Place this directory somewhere on Python's `sys.path` (install
it with pip, or set `PYTHONPATH`).

### Verifying the Plugin Works

#### 1. Check startup logs

When the plugin registers, the manager logs:

```
INFO Plugin registered: audit_logger
```

If loading fails:

```
ERROR Failed to load plugin from my_audit_plugin.plugin.AuditLoggerPlugin: ...
```

#### 2. Trigger a tool call and check the audit file

```bash
# After making a tool call:
cat audit.log
# {"slug": "dev", "tool": "search_issues", "duration_ms": 1520.4, "success": true}
```

#### 3. Check `plugin_manager.plugins`

```python
from toolatlas_mcp.plugin import plugin_manager
print([p.name for p in plugin_manager.plugins])
# ['cache', 'metrics', 'audit_logger']
```

#### 4. Verify error isolation

Test that a broken plugin doesn't crash the app:

```python
class BrokenPlugin(Plugin):
    name = "broken"

    async def on_before_tool_call(self, ctx):
        raise RuntimeError("Something went wrong")

await plugin_manager.register(BrokenPlugin())
# The call will be logged as ERROR, but the tool call still succeeds
# Other plugins still receive the event
```
