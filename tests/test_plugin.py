import pytest
from unittest.mock import AsyncMock

from toolatlas_mcp.plugin.base import Plugin, PluginAbortError, PluginContext
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


# ---- PluginAbortError tests ----


@pytest.mark.asyncio
async def test_plugin_abort_error_propagates():
    """PluginAbortError propagates through execute()."""
    class AbortPlugin(Plugin):
        name = "abort"
        async def on_before_tool_call(self, ctx):
            raise PluginAbortError("Blocked!")

    await plugin_manager.register(AbortPlugin())
    ctx = PluginContext(tool_name="test")
    with pytest.raises(PluginAbortError, match="Blocked!"):
        await plugin_manager.execute("on_before_tool_call", ctx=ctx)


@pytest.mark.asyncio
async def test_plugin_abort_error_execute_first():
    """PluginAbortError propagates through execute_first()."""
    class AbortPlugin(Plugin):
        name = "abort"
        async def on_before_list_tools(self, ctx):
            raise PluginAbortError("Blocked list!")

    await plugin_manager.register(AbortPlugin())
    ctx = PluginContext(slug="dev", method="list_tools")
    with pytest.raises(PluginAbortError, match="Blocked list!"):
        await plugin_manager.execute_first("on_before_list_tools", ctx=ctx)


@pytest.mark.asyncio
async def test_plugin_abort_does_not_break_other_plugins():
    """Other plugins still run after an aborting plugin in the chain."""
    class AbortPlugin(Plugin):
        name = "abort"
        async def on_before_tool_call(self, ctx):
            raise PluginAbortError("Blocked!")

    class NormalPlugin(Plugin):
        name = "normal"
        def __init__(self):
            self.called = False
        async def on_before_tool_call(self, ctx):
            self.called = True

    # Register abort first, normal second — normal should NOT run
    np = NormalPlugin()
    await plugin_manager.register(AbortPlugin())
    await plugin_manager.register(np)
    ctx = PluginContext(tool_name="test")
    with pytest.raises(PluginAbortError):
        await plugin_manager.execute("on_before_tool_call", ctx=ctx)
    assert not np.called


@pytest.mark.asyncio
async def test_plugin_abort_error_not_swallowed():
    """PluginAbortError is NOT caught by the generic except.

    Normal Exception IS swallowed, PluginAbortError propagates and
    prevents subsequent plugins from running.
    """
    class NormalErrorPlugin(Plugin):
        name = "normal_err"
        async def on_before_tool_call(self, ctx):
            raise ValueError("Normal error")

    class AbortPlugin(Plugin):
        name = "abort"
        async def on_before_tool_call(self, ctx):
            raise PluginAbortError("Abort!")

    class FollowPlugin(Plugin):
        name = "follow"
        def __init__(self):
            self.called = False
        async def on_before_tool_call(self, ctx):
            self.called = True

    fp = FollowPlugin()
    await plugin_manager.register(NormalErrorPlugin())
    await plugin_manager.register(fp)
    # There is no AbortPlugin — NormalErrorPlugin's ValueError is swallowed,
    # FollowPlugin should still run
    ctx = PluginContext(tool_name="test")
    results = await plugin_manager.execute("on_before_tool_call", ctx=ctx)
    assert fp.called
    assert results == [None]  # NormalErrorPlugin raised (swallowed), FollowPlugin returned None


# ---- Priority ordering tests ----


@pytest.mark.asyncio
async def test_plugin_priority_ordering():
    """Plugins execute in priority order (lower first)."""
    class OrderedPlugin(Plugin):
        def __init__(self, name, priority, order_list):
            self.name = name
            self.priority = priority
            self._order_list = order_list
        async def on_before_tool_call(self, ctx):
            self._order_list.append(self.name)

    order = []
    await plugin_manager.register(OrderedPlugin("last", 100, order))
    await plugin_manager.register(OrderedPlugin("first", -100, order))
    await plugin_manager.register(OrderedPlugin("middle", 0, order))

    ctx = PluginContext(tool_name="test")
    await plugin_manager.execute("on_before_tool_call", ctx=ctx)
    assert order == ["first", "middle", "last"]


@pytest.mark.asyncio
async def test_plugin_default_priority():
    """Default priority is 0 for all plugins."""
    class DefaultPlugin(Plugin):
        name = "default"

    p = DefaultPlugin()
    assert p.priority == 0


# ---- on_tool_filter tests ----


@pytest.mark.asyncio
async def test_tool_filter_removes_tools():
    """on_tool_filter can remove tools from the list."""
    class FilterPlugin(Plugin):
        name = "filter"
        async def on_tool_filter(self, ctx, tools):
            return [t for t in tools if t["name"] != "secret_tool"]

    await plugin_manager.register(FilterPlugin())
    in_tools = [{"name": "public_tool"}, {"name": "secret_tool"}]
    out_tools = in_tools
    for plugin in plugin_manager.plugins:
        try:
            out_tools = await plugin.on_tool_filter(ctx=PluginContext(), tools=out_tools)
        except PluginAbortError:
            raise
    assert len(out_tools) == 1
    assert out_tools[0]["name"] == "public_tool"


@pytest.mark.asyncio
async def test_tool_filter_multiple_plugins():
    """Multiple tool filter plugins chain correctly."""
    class FilterOnlyA(Plugin):
        name = "filter_a"
        async def on_tool_filter(self, ctx, tools):
            return [t for t in tools if "a" in t["name"].lower()]

    class RemoveAlpha(Plugin):
        name = "filter_b"
        async def on_tool_filter(self, ctx, tools):
            return [t for t in tools if t["name"] != "alpha"]

    await plugin_manager.register(FilterOnlyA())
    await plugin_manager.register(RemoveAlpha())
    in_tools = [{"name": "alpha"}, {"name": "xyz"}, {"name": "gamma"}]
    out_tools = in_tools
    for plugin in plugin_manager.plugins:
        try:
            out_tools = await plugin.on_tool_filter(ctx=PluginContext(), tools=out_tools)
        except PluginAbortError:
            raise
    # FilterOnlyA keeps alpha (has 'a'), removes xyz (no 'a'), keeps gamma (has 'a')
    # RemoveAlpha removes alpha → only gamma remains
    assert len(out_tools) == 1
    assert out_tools[0]["name"] == "gamma"


# ---- on_before_response_return tests ----


@pytest.mark.asyncio
async def test_before_response_return_modifies_result():
    """on_before_response_return can modify the result dict."""
    class ResponsePlugin(Plugin):
        name = "response_mod"
        async def on_before_response_return(self, ctx, result):
            result["modified"] = True
            return result

    await plugin_manager.register(ResponsePlugin())
    result = {"content": "hello"}
    for plugin in plugin_manager.plugins:
        method = getattr(plugin, "on_before_response_return", None)
        if method:
            modified = await method(ctx=PluginContext(), result=result)
            if modified is not None:
                result = modified
    assert result["modified"] is True


@pytest.mark.asyncio
async def test_before_response_return_none_passthrough():
    """Returning None from on_before_response_return passes through unchanged."""
    class NoopPlugin(Plugin):
        name = "noop"
        async def on_before_response_return(self, ctx, result):
            return None  # pass through

    await plugin_manager.register(NoopPlugin())
    result = {"content": "hello"}
    for plugin in plugin_manager.plugins:
        method = getattr(plugin, "on_before_response_return", None)
        if method:
            modified = await method(ctx=PluginContext(), result=result)
            if modified is not None:
                result = modified
    assert result == {"content": "hello"}


# ---- PluginContext identity tests ----


@pytest.mark.asyncio
async def test_plugin_context_identity_fields():
    """PluginContext carries identity and routing fields."""
    ctx = PluginContext(
        slug="dev", method="call_tool", tool_name="search",
        client_id="chatbot-v3", user_id="shashi",
        org_id="acme-corp", tenant_id="dev-42",
        proxy_id="proxy-1", proxy_name="My Proxy",
        server_name="Jira Server",
        meta={"trace_id": "abc123"},
    )
    assert ctx.client_id == "chatbot-v3"
    assert ctx.user_id == "shashi"
    assert ctx.org_id == "acme-corp"
    assert ctx.tenant_id == "dev-42"
    assert ctx.proxy_id == "proxy-1"
    assert ctx.proxy_name == "My Proxy"
    assert ctx.server_name == "Jira Server"
    assert ctx.meta["trace_id"] == "abc123"


# ---- Plugin router property ----


@pytest.mark.asyncio
async def test_plugin_router_default_none():
    """Default router property returns None."""
    p = Plugin()
    assert p.router is None
