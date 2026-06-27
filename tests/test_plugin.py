import pytest
from unittest.mock import AsyncMock

from toolatlas_mcp.plugin.base import Plugin, PluginContext
from toolatlas_mcp.plugin.manager import PluginManager, plugin_manager


@pytest.fixture(autouse=True)
async def reset_plugins():
    await plugin_manager.clear()
    yield
    await plugin_manager.clear()


# ---- Test plugin implementations ----

class LoggingPlugin(Plugin):
    name = "logger"
    def __init__(self):
        self.calls = []

    async def on_before_list_tools(self, ctx):
        self.calls.append(("before_list_tools", ctx.slug))
        return None

    async def on_after_list_tools(self, ctx, tools):
        self.calls.append(("after_list_tools", len(tools)))

    async def on_before_tool_call(self, ctx):
        self.calls.append(("before_tool_call", ctx.tool_name))

    async def on_after_tool_call(self, ctx, result):
        self.calls.append(("after_tool_call", ctx.tool_name))

    async def on_server_connected(self, server_id):
        self.calls.append(("server_connected", server_id))

    async def on_tool_added(self, server_id, tool_names):
        self.calls.append(("tool_added", server_id, tool_names))


class ShortCircuitPlugin(Plugin):
    name = "short_circuit"

    async def on_before_list_tools(self, ctx):
        return [{"name": "shortcut_tool", "description": "Bypassed"}]


class MetricPlugin(Plugin):
    name = "metrics"
    def __init__(self):
        self.call_count = 0

    async def on_after_tool_call(self, ctx, result):
        self.call_count += 1


# ---- Tests ----

@pytest.mark.asyncio
async def test_plugin_lifecycle():
    """3.1 Plugin startup and shutdown are called."""
    p = LoggingPlugin()
    await plugin_manager.register(p)
    assert p in plugin_manager.plugins

    await plugin_manager.shutdown_all()
    assert len(plugin_manager.plugins) == 0


@pytest.mark.asyncio
async def test_execute_before_list_tools():
    """3.2 Plugin can observe list_tools."""
    p = LoggingPlugin()
    await plugin_manager.register(p)

    ctx = PluginContext(slug="dev", method="list_tools")
    await plugin_manager.execute("on_before_list_tools", ctx=ctx)
    assert len(p.calls) == 1
    assert p.calls[0] == ("before_list_tools", "dev")


@pytest.mark.asyncio
async def test_execute_first_short_circuits():
    """3.2 Plugin returning tools short-circuits."""
    await plugin_manager.register(ShortCircuitPlugin())

    ctx = PluginContext(slug="dev", method="list_tools")
    result = await plugin_manager.execute_first("on_before_list_tools", ctx=ctx)
    assert result is not None
    assert result[0]["name"] == "shortcut_tool"


@pytest.mark.asyncio
async def test_multiple_plugins_all_called():
    """3.3 Both plugins receive the same event."""
    p1 = LoggingPlugin()
    p2 = LoggingPlugin()
    await plugin_manager.register(p1)
    await plugin_manager.register(p2)

    ctx = PluginContext(slug="dev", method="list_tools")
    await plugin_manager.execute("on_before_list_tools", ctx=ctx)
    assert len(p1.calls) == 1
    assert len(p2.calls) == 1


@pytest.mark.asyncio
async def test_execute_after_tool_call():
    """3.5 after_tool_call receives the result."""
    p = LoggingPlugin()
    await plugin_manager.register(p)

    ctx = PluginContext(tool_name="search_code")
    await plugin_manager.execute("on_after_tool_call", ctx=ctx, result={"content": "ok"})
    assert len(p.calls) == 1
    assert p.calls[0][0] == "after_tool_call"


@pytest.mark.asyncio
async def test_plugin_tool_added_notification():
    """3.7 Plugin notified when tools are added."""
    p = LoggingPlugin()
    await plugin_manager.register(p)

    await plugin_manager.execute("on_tool_added", server_id="s1", tool_names=["t1", "t2"])
    assert any(c[0] == "tool_added" for c in p.calls)


@pytest.mark.asyncio
async def test_short_circuit_cache_lookup():
    """3.8 Plugin returning cache data short-circuits."""
    class CachePlugin(Plugin):
        name = "cache"
        async def on_before_cache_lookup(self, slug):
            return (123.0, [{"name": "cached_tool"}])

    p = CachePlugin()
    await plugin_manager.register(p)
    result = await plugin_manager.execute_first("on_before_cache_lookup", slug="dev")
    assert result is not None
    assert result[1][0]["name"] == "cached_tool"


@pytest.mark.asyncio
async def test_plugin_error_does_not_break_core():
    """3.12 Plugin raising in hook is logged but doesn't break chain."""
    class BrokenPlugin(Plugin):
        name = "broken"
        async def on_before_list_tools(self, ctx):
            raise RuntimeError("Boom!")

    p = LoggingPlugin()
    await plugin_manager.register(BrokenPlugin())
    await plugin_manager.register(p)

    ctx = PluginContext(slug="dev", method="list_tools")
    results = await plugin_manager.execute("on_before_list_tools", ctx=ctx)
    # Broken plugin's error is logged, but other plugins still run
    assert len(p.calls) == 1
    assert len(results) == 1  # only LoggingPlugin returned; BrokenPlugin raised
    assert results[0] is None


@pytest.mark.asyncio
async def test_metrics_plugin_records_call():
    """3.9 Metrics plugin increments counter on tool call."""
    mp = MetricPlugin()
    await plugin_manager.register(mp)

    ctx = PluginContext(tool_name="search_code")
    await plugin_manager.execute("on_after_tool_call", ctx=ctx, result={})
    assert mp.call_count == 1

    await plugin_manager.execute("on_after_tool_call", ctx=ctx, result={})
    assert mp.call_count == 2


@pytest.mark.asyncio
async def test_plugin_discovery_entry_point():
    """3.10 Load plugin from dotted path."""
    # We test the module itself (builtins cache plugin)
    await plugin_manager.load_from_entry_point("toolatlas_mcp.plugin.builtins.cache")
    names = [p.name for p in plugin_manager.plugins]
    assert "cache" in names


@pytest.mark.asyncio
async def test_all_hooks_optional():
    """3.12 Plugin with no hooks defined doesn't cause errors."""
    class MinimalPlugin(Plugin):
        name = "minimal"

    p = MinimalPlugin()
    await plugin_manager.register(p)
    # Should not raise
    await plugin_manager.execute("on_before_list_tools", ctx=PluginContext())
    await plugin_manager.execute("on_after_list_tools", ctx=PluginContext(), tools=[])
    await plugin_manager.execute("on_before_tool_call", ctx=PluginContext())
    await plugin_manager.execute("on_after_tool_call", ctx=PluginContext(), result={})
    await plugin_manager.execute("on_server_connected", server_id="s1")
    await plugin_manager.execute("on_tool_added", server_id="s1", tool_names=[])
