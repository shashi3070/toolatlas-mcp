# Plugin System — Testing

This document covers how to test plugin hooks, mock dependencies, verify
error isolation, and validate short-circuit behavior.

See [plugin-examples.md](plugin-examples.md) for the plugins referenced below.

## Test Patterns

### Testing a Single Hook

```python
import pytest
from toolatlas_mcp.plugin import Plugin, PluginManager, PluginContext

class MyPlugin(Plugin):
    name = "my_plugin"

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        ctx.extra["checked"] = True


@pytest.mark.asyncio
async def test_on_before_tool_call():
    mgr = PluginManager()
    plugin = MyPlugin()
    await mgr.register(plugin)

    ctx = PluginContext(slug="test", method="call_tool", tool_name="test_tool")
    await mgr.execute("on_before_tool_call", ctx=ctx)

    assert ctx.extra.get("checked") is True
```

### Testing `on_after_list_tools` — Modifying tools

```python
class EnrichPlugin(Plugin):
    name = "enricher"
    async def on_after_list_tools(self, ctx: PluginContext, tools: list[dict]) -> None:
        for t in tools:
            t["description"] = t["description"] + " [enriched]"


@pytest.mark.asyncio
async def test_enrich_plugin_adds_suffix():
    mgr = PluginManager()
    await mgr.register(EnrichPlugin())

    ctx = PluginContext(slug="dev", method="list_tools")
    tools = [{"name": "search", "description": "Original"}]
    await mgr.execute("on_after_list_tools", ctx=ctx, tools=tools)

    assert tools[0]["description"] == "Original [enriched]"
```

### Testing Short-Circuit Behavior

Use `execute_first` to test that only the first non-None result is returned:

```python
class CachePluginA(Plugin):
    name = "cache_a"
    async def on_before_cache_lookup(self, slug: str):
        return (100.0, [{"name": "from_A"}])

class CachePluginB(Plugin):
    name = "cache_b"
    async def on_before_cache_lookup(self, slug: str):
        return (200.0, [{"name": "from_B"}])  # Never reached


@pytest.mark.asyncio
async def test_execute_first_short_circuits():
    mgr = PluginManager()
    await mgr.register(CachePluginA())
    await mgr.register(CachePluginB())

    result = await mgr.execute_first("on_before_cache_lookup", slug="dev")

    assert result is not None
    timestamp, tools = result
    assert tools[0]["name"] == "from_A"
```

### Testing Error Isolation

A broken plugin should not prevent other plugins from running:

```python
class GoodPlugin(Plugin):
    name = "good"
    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        ctx.extra["good_ran"] = True

class BadPlugin(Plugin):
    name = "bad"
    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        raise RuntimeError("I am broken")


@pytest.mark.asyncio
async def test_error_isolation():
    mgr = PluginManager()
    await mgr.register(GoodPlugin())
    await mgr.register(BadPlugin())

    ctx = PluginContext(slug="test", method="call_tool")
    await mgr.execute("on_before_tool_call", ctx=ctx)

    # Good plugin still ran despite BadPlugin raising
    assert ctx.extra.get("good_ran") is True
```

### Testing `on_before_tool_call` that raises to block

```python
class BlockingPlugin(Plugin):
    name = "blocker"
    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        if ctx.tool_name == "delete_repo":
            raise PermissionError("delete_repo is not allowed")


@pytest.mark.asyncio
async def test_blocking_plugin_raises():
    mgr = PluginManager()
    await mgr.register(BlockingPlugin())

    ctx = PluginContext(slug="test", method="call_tool", tool_name="delete_repo")
    with pytest.raises(PermissionError, match="not allowed"):
        await mgr.execute("on_before_tool_call", ctx=ctx)
```

### Testing Lifecycle Hooks

```python
class LifecyclePlugin(Plugin):
    name = "lifecycle"
    def __init__(self):
        self.events = []

    async def startup(self):
        self.events.append("startup")

    async def shutdown(self):
        self.events.append("shutdown")


@pytest.mark.asyncio
async def test_lifecycle():
    mgr = PluginManager()
    plugin = LifecyclePlugin()
    await mgr.register(plugin)
    assert "startup" in plugin.events
    assert plugin in mgr.plugins

    await mgr.clear()
    assert "shutdown" in plugin.events
    assert mgr.plugins == []
```

## Testing the PluginManager Itself

### Test hook ordering (registration order matters)

```python
@pytest.mark.asyncio
async def test_execution_order():
    mgr = PluginManager()
    results = []

    class FirstPlugin(Plugin):
        name = "first"
        async def on_after_list_tools(self, ctx, tools):
            results.append("first")

    class SecondPlugin(Plugin):
        name = "second"
        async def on_after_list_tools(self, ctx, tools):
            results.append("second")

    await mgr.register(FirstPlugin())
    await mgr.register(SecondPlugin())

    ctx = PluginContext(slug="test", method="list_tools")
    await mgr.execute("on_after_list_tools", ctx=ctx, tools=[])

    assert results == ["first", "second"]
```

### Test `execute_first` returns None when all plugins return None

```python
class NonePlugin(Plugin):
    name = "none_ret"
    async def on_before_cache_lookup(self, slug: str):
        return None


@pytest.mark.asyncio
async def test_execute_first_none_when_all_none():
    mgr = PluginManager()
    await mgr.register(NonePlugin())
    result = await mgr.execute_first("on_before_cache_lookup", slug="dev")
    assert result is None
```

## Current Test Coverage

The test suite `tests/test_plugin.py` covers:

| Test | What It Verifies |
|------|-----------------|
| `test_plugin_lifecycle` | `startup`/`shutdown`/`clear` |
| `test_execute_first_short_circuits` | First non-None result stops iteration |
| `test_multiple_plugins_all_called` | Every plugin receives the event |
| `test_execute_after_tool_call` | Result is passed to `on_after_tool_call` |
| `test_plugin_tool_added_notification` | `on_tool_added` fires correctly |
| `test_short_circuit_cache_lookup` | Cache bypass via `execute_first` |
| `test_plugin_error_does_not_break_core` | Error isolation |
| `test_metrics_plugin_records_call` | Metrics counter increments |
| `test_plugin_discovery_entry_point` | Loading via dotted path |
| `test_all_hooks_optional` | Plugin with no hooks runs without error |

Run them with:

```bash
pytest tests/test_plugin.py -v
```
