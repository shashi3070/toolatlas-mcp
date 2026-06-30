"""End-to-end test for the _meta protocol through the real proxy message endpoint.

Each test creates its own proxy with a unique slug to avoid engine state sharing.
"""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.usefixtures("start_mcp_servers")
class TestMetaE2E:

    async def _create_test_proxy(self, ac: AsyncClient, suffix: str) -> str:
        """Create a proxy linked to the GitHub test MCP server (port 9001)."""
        slug = f"e2e-{suffix}"
        # Create server (use POST; returns 201)
        resp = await ac.post("/api/servers", json={
            "name": f"e2e-srv-{suffix}",
            "transport": "sse",
            "url": "http://127.0.0.1:9001",
        })
        assert resp.status_code in (200, 201), f"Server create failed: {resp.text}"
        server = resp.json()

        # Discover tools
        resp = await ac.post(f"/api/servers/{server['id']}/discover")
        assert resp.status_code == 200, f"Discover failed: {resp.text}"

        # Create proxy
        resp = await ac.post("/api/proxies", json={
            "name": f"e2e-proxy-{suffix}",
            "slug": slug,
            "description": "E2E test proxy",
        })
        assert resp.status_code in (200, 201), f"Proxy create failed: {resp.text}"
        proxy = resp.json()

        # Link server to proxy
        resp = await ac.post(f"/api/proxies/{proxy['id']}/servers", json={
            "server_id": server["id"],
        })
        assert resp.status_code in (200, 201), f"Link failed: {resp.text}"

        # Enable all tools
        resp = await ac.get(f"/api/proxies/{proxy['id']}/tools")
        for t in resp.json():
            await ac.patch(f"/api/proxies/{proxy['id']}/tools/{t['id']}", json={"enabled": True})

        return slug

    async def test_full_meta(self, seeded_client: AsyncClient):
        slug = await self._create_test_proxy(seeded_client, "full")
        session_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        # Initialize
        await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "e2e", "version": "1.0"}},
        })
        await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "method": "notifications/initialized",
        })

        # Call tool with full meta
        resp = await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "id": 3, "method": "call_tool",
            "params": {"name": "search_code", "arguments": {"query": "e2e"}, "_meta": {
                "trace_id": trace_id, "span_id": span_id,
                "org_id": "e2e-org", "tenant_id": "e2e-tenant", "user_id": "e2e-user",
            }},
        })
        assert resp.status_code == 202

        import asyncio
        await asyncio.sleep(0.5)

        resp = await seeded_client.get("/api/analytics/calls", params={"limit": 50})
        calls = resp.json()
        our = [c for c in calls if c.get("trace_id") == trace_id]
        assert len(our) >= 1, f"No call with trace_id {trace_id} among {len(calls)} calls"
        c = our[0]
        assert c["span_id"] == span_id
        assert c["org_id"] == "e2e-org"
        assert c["tenant_id"] == "e2e-tenant"
        assert c["user_id"] == "e2e-user"
        assert c["tool_name"] == "search_code"

    async def test_minimal_meta(self, seeded_client: AsyncClient):
        slug = await self._create_test_proxy(seeded_client, "minimal")
        session_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())

        await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "e2e", "version": "1.0"}},
        })
        await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "method": "notifications/initialized",
        })

        resp = await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "id": 3, "method": "call_tool",
            "params": {"name": "search_code", "arguments": {"query": "minimal"}, "_meta": {"trace_id": trace_id}},
        })
        assert resp.status_code == 202

        import asyncio
        await asyncio.sleep(0.5)

        resp = await seeded_client.get("/api/analytics/calls", params={"limit": 50})
        calls = resp.json()
        our = [c for c in calls if c.get("trace_id") == trace_id]
        assert len(our) >= 1, f"No call found with trace_id {trace_id}"
        c = our[0]
        assert c["span_id"] is not None
        assert len(c["span_id"]) > 0
        assert c.get("org_id") is None
        assert c.get("tenant_id") is None
        assert c.get("user_id") is None

    async def test_chained_spans(self, seeded_client: AsyncClient):
        slug = await self._create_test_proxy(seeded_client, "chain")
        session_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        span_1 = str(uuid.uuid4())
        span_2 = str(uuid.uuid4())

        await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "e2e", "version": "1.0"}},
        })
        await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "method": "notifications/initialized",
        })

        # First call
        await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "id": 3, "method": "call_tool",
            "params": {"name": "search_code", "arguments": {"query": "first"}, "_meta": {"trace_id": trace_id, "span_id": span_1}},
        })

        # Second call (child)
        await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "id": 4, "method": "call_tool",
            "params": {"name": "search_code", "arguments": {"query": "second"}, "_meta": {"trace_id": trace_id, "span_id": span_2, "parent_span_id": span_1}},
        })

        import asyncio
        await asyncio.sleep(0.5)

        resp = await seeded_client.get(f"/api/graph/trace/{trace_id}")
        assert resp.status_code == 200, f"Trace graph failed: {resp.text}"
        data = resp.json()
        nodes = data["nodes"]
        first_node = next((n for n in nodes if n["span_id"] == span_1), None)
        second_node = next((n for n in nodes if n["span_id"] == span_2), None)
        assert first_node is not None
        assert second_node is not None
        assert first_node["parent_span_id"] is None
        assert second_node["parent_span_id"] == span_1
        edge_pairs = {(e["source"], e["target"]) for e in data["edges"]}
        assert (first_node["id"], second_node["id"]) in edge_pairs

    async def test_tenant_filter(self, seeded_client: AsyncClient):
        slug = await self._create_test_proxy(seeded_client, "tnt")
        session_id = str(uuid.uuid4())

        await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "e2e", "version": "1.0"}},
        })
        await seeded_client.post(f"/proxy/{slug}/message/{session_id}", json={
            "jsonrpc": "2.0", "method": "notifications/initialized",
        })

        # Two calls with different org_ids via separate session_ids
        async def _call(org_id: str):
            sid = str(uuid.uuid4())
            await seeded_client.post(f"/proxy/{slug}/message/{sid}", json={
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "e2e", "version": "1.0"}},
            })
            await seeded_client.post(f"/proxy/{slug}/message/{sid}", json={
                "jsonrpc": "2.0", "method": "notifications/initialized",
            })
            await seeded_client.post(f"/proxy/{slug}/message/{sid}", json={
                "jsonrpc": "2.0", "id": 3, "method": "call_tool",
                "params": {"name": "search_code", "arguments": {"query": org_id}, "_meta": {"trace_id": str(uuid.uuid4()), "org_id": org_id}},
            })

        await _call("org-a")
        await _call("org-b")

        import asyncio
        await asyncio.sleep(0.5)

        resp_a = await seeded_client.get("/api/analytics/calls", params={"org_id": "org-a"})
        assert resp_a.status_code == 200
        assert all(c["org_id"] == "org-a" for c in resp_a.json())

        resp_b = await seeded_client.get("/api/analytics/calls", params={"org_id": "org-b"})
        assert resp_b.status_code == 200
        assert all(c["org_id"] == "org-b" for c in resp_b.json())
