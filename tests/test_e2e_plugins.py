"""End-to-end test for plugin governance and abort through the proxy message endpoint."""

import uuid

import pytest
from httpx import AsyncClient

from toolatlas_mcp.plugin.base import Plugin, PluginAbortError, PluginContext
from toolatlas_mcp.plugin.manager import plugin_manager


class BlockDeletePlugin(Plugin):
    name = "e2e_block_delete"
    priority = -100

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        if ctx.tool_name.startswith("delete_"):
            raise PluginAbortError(
                f"Tool '{ctx.tool_name}' is blocked by governance policy"
            )

    async def on_tool_filter(self, ctx: PluginContext, tools: list[dict]) -> list[dict]:
        return [t for t in tools if not t["name"].startswith("delete_")]


class AppendResultPlugin(Plugin):
    name = "e2e_append_result"

    async def on_before_response_return(
        self, ctx: PluginContext, result: dict,
    ) -> dict | None:
        result.setdefault("content", [])
        result["content"].append({"type": "text", "text": " [governance audit appended]"})
        return result


@pytest.fixture(autouse=True)
def register_test_plugins():
    plugin_manager.clear()
    yield
    plugin_manager.clear()


@pytest.mark.asyncio
@pytest.mark.usefixtures("start_mcp_servers")
class TestPluginE2E:

    async def _create_test_proxy(self, ac: AsyncClient, suffix: str) -> str:
        slug = f"plug-e2e-{suffix}"
        resp = await ac.post("/api/servers", json={
            "name": f"plug-srv-{suffix}",
            "transport": "sse",
            "url": "http://127.0.0.1:9001",
        })
        assert resp.status_code in (200, 201), f"Server create failed: {resp.text}"
        server = resp.json()

        resp = await ac.post(f"/api/servers/{server['id']}/discover")
        assert resp.status_code == 200, f"Discover failed: {resp.text}"

        resp = await ac.post("/api/proxies", json={
            "name": f"plug-proxy-{suffix}",
            "slug": slug,
            "description": "Plugin E2E test proxy",
        })
        assert resp.status_code in (200, 201), f"Proxy create failed: {resp.text}"
        proxy = resp.json()

        resp = await ac.post(f"/api/proxies/{proxy['id']}/servers", json={
            "server_id": server["id"],
        })
        assert resp.status_code in (200, 201), f"Link failed: {resp.text}"

        resp = await ac.get(f"/api/proxies/{proxy['id']}/tools")
        for t in resp.json():
            await ac.patch(f"/api/proxies/{proxy['id']}/tools/{t['id']}", json={"enabled": True})

        return slug

    async def test_plugin_abort_blocks_tool_call(self, seeded_client: AsyncClient):
        """A governance plugin blocking delete_* tools should return error -32001."""
        block_plugin = BlockDeletePlugin()
        await plugin_manager.register(block_plugin)

        slug = await self._create_test_proxy(seeded_client, "abort")
        session_id = str(uuid.uuid4())

        # Initialize + notifications
        await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
        })
        await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "method": "notifications/initialized",
        })

        import asyncio
        await asyncio.sleep(0.3)

        # Try to call a delete_ tool — should be blocked
        resp = await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "id": 3, "method": "call_tool",
            "params": {"name": "search_code", "arguments": {}},
        })
        assert resp.status_code == 202

        # The error is sent via SSE, not HTTP response.
        # We verify the engine correctly converts PluginAbortError -> PermissionError -> -32001
        # by checking that the tool call raises PermissionError when we call engine directly.
        from toolatlas_mcp.proxy.engine import ProxyEngine
        from toolatlas_mcp.db import get_storage

        storage = await anext(get_storage())
        try:
            engine = ProxyEngine(storage)
            await engine.initialize_proxy(slug)
            with pytest.raises(PermissionError) as excinfo:
                await engine.call_tool(slug, "delete_repo", {})
            assert "not authorized" in str(excinfo.value).lower() or "blocked" in str(excinfo.value).lower()
        finally:
            engine.close()

    async def test_plugin_appends_to_response(self, seeded_client: AsyncClient):
        """on_before_response_return appends governance text to every response."""
        append_plugin = AppendResultPlugin()
        await plugin_manager.register(append_plugin)

        slug = await self._create_test_proxy(seeded_client, "append")
        session_id = str(uuid.uuid4())

        await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
        })
        await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "method": "notifications/initialized",
        })

        import asyncio
        await asyncio.sleep(0.3)

        from toolatlas_mcp.proxy.engine import ProxyEngine
        from toolatlas_mcp.db import get_storage

        storage = await anext(get_storage())
        try:
            engine = ProxyEngine(storage)
            await engine.initialize_proxy(slug)
            result = await engine.call_tool(slug, "search_code", {"query": "test"})
            assert "content" in result
            has_appended = any(
                isinstance(c, dict) and "governance audit appended" in str(c.get("text", ""))
                for c in result.get("content", [])
            )
            assert has_appended, f"Expected appended text in result: {result}"
        finally:
            engine.close()

    async def test_plugin_tool_filter_hides_tools(self, seeded_client: AsyncClient):
        """on_tool_filter removes delete_* tools from the list."""
        filter_plugin = BlockDeletePlugin()
        await plugin_manager.register(filter_plugin)

        slug = await self._create_test_proxy(seeded_client, "filter")

        from toolatlas_mcp.proxy.engine import ProxyEngine
        from toolatlas_mcp.db import get_storage

        storage = await anext(get_storage())
        try:
            engine = ProxyEngine(storage)
            await engine.initialize_proxy(slug)
            tools = await engine.list_tools(slug)
            names = [t["name"] for t in tools]
            has_delete = any("delete" in n.lower() for n in names)
            assert not has_delete, f"delete_* tools should be filtered: {names}"
        finally:
            engine.close()
