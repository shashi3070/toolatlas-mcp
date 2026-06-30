import uuid

import httpx
import pytest
from toolatlas_mcp.api.app import create_app
from toolatlas_mcp.db import get_storage


@pytest.mark.asyncio
async def test_record_call_stores_meta_fields(repo):
    call = await repo.record_call(
        tool_name="test_tool",
        trace_id="trace-1",
        span_id="span-1",
        parent_span_id="parent-1",
        org_id="org-acme",
        tenant_id="tenant-alpha",
        user_id="user-42",
    )
    assert call["trace_id"] == "trace-1"
    assert call["span_id"] == "span-1"
    assert call["parent_span_id"] == "parent-1"
    assert call["org_id"] == "org-acme"
    assert call["tenant_id"] == "tenant-alpha"
    assert call["user_id"] == "user-42"


@pytest.mark.asyncio
async def test_record_call_auto_fields(repo):
    call = await repo.record_call(tool_name="auto_test")
    assert call["trace_id"] is None
    assert call["span_id"] is None
    assert call["parent_span_id"] is None
    assert call["org_id"] is None
    assert call["tenant_id"] is None
    assert call["user_id"] is None


@pytest.mark.asyncio
async def test_list_calls_filters_by_org_and_tenant(repo):
    await repo.record_call(tool_name="t1", org_id="org-a", tenant_id="tnt-1")
    await repo.record_call(tool_name="t2", org_id="org-a", tenant_id="tnt-2")
    await repo.record_call(tool_name="t3", org_id="org-b", tenant_id="tnt-1")

    calls_org_a = await repo.list_calls(org_id="org-a")
    assert len(calls_org_a) >= 2
    assert all(c["org_id"] == "org-a" for c in calls_org_a)

    calls_tnt1 = await repo.list_calls(tenant_id="tnt-1")
    assert len(calls_tnt1) >= 2
    assert all(c["tenant_id"] == "tnt-1" for c in calls_tnt1)

    calls_both = await repo.list_calls(org_id="org-a", tenant_id="tnt-1")
    assert len(calls_both) >= 1
    assert all(c["org_id"] == "org-a" and c["tenant_id"] == "tnt-1" for c in calls_both)


class _SpanTreeStorage:
    def __init__(self, trace_id):
        self.trace_id = trace_id

    async def list_calls(self, **kw):
        return [
            {"id": "c1", "trace_id": self.trace_id, "span_id": "span-root", "parent_span_id": None, "tool_name": "root_tool", "duration_ms": 100, "success": True, "timestamp": "2025-01-01T00:00:00Z"},
            {"id": "c2", "trace_id": self.trace_id, "span_id": "span-child-1", "parent_span_id": "span-root", "tool_name": "child_tool", "duration_ms": 50, "success": True, "timestamp": "2025-01-01T00:00:01Z"},
            {"id": "c3", "trace_id": self.trace_id, "span_id": "span-child-2", "parent_span_id": "span-child-1", "tool_name": "grandchild_tool", "duration_ms": 25, "success": True, "timestamp": "2025-01-01T00:00:02Z"},
        ]
    async def get_call(self, call_id): return None
    async def list_traces(self): return []


@pytest.mark.asyncio
async def test_trace_graph_builds_span_tree():
    trace_id = str(uuid.uuid4())
    app = create_app()
    app.dependency_overrides[get_storage] = lambda: _SpanTreeStorage(trace_id)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/graph/trace/{trace_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trace_id"] == trace_id
        assert len(data["nodes"]) == 3

        root = next(n for n in data["nodes"] if n["tool_name"] == "root_tool")
        child = next(n for n in data["nodes"] if n["tool_name"] == "child_tool")
        grandchild = next(n for n in data["nodes"] if n["tool_name"] == "grandchild_tool")

        assert root["span_id"] == "span-root"
        assert child["parent_span_id"] == "span-root"
        assert grandchild["parent_span_id"] == "span-child-1"

        edges = data["edges"]
        assert len(edges) == 2
        edge_pairs = {(e["source"], e["target"]) for e in edges}
        assert (root["id"], child["id"]) in edge_pairs
        assert (child["id"], grandchild["id"]) in edge_pairs


class _ChronoStorage:
    def __init__(self, trace_id):
        self.trace_id = trace_id

    async def list_calls(self, **kw):
        return [
            {"id": "c1", "trace_id": self.trace_id, "span_id": None, "parent_span_id": None, "tool_name": "first", "duration_ms": 10, "success": True, "timestamp": "2025-01-01T00:00:00Z"},
            {"id": "c2", "trace_id": self.trace_id, "span_id": None, "parent_span_id": None, "tool_name": "second", "duration_ms": 20, "success": True, "timestamp": "2025-01-01T00:00:01Z"},
        ]
    async def get_call(self, call_id): return None
    async def list_traces(self): return []


@pytest.mark.asyncio
async def test_trace_graph_chronological_fallback():
    trace_id = str(uuid.uuid4())
    app = create_app()
    app.dependency_overrides[get_storage] = lambda: _ChronoStorage(trace_id)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/graph/trace/{trace_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["edges"]) == 1
        assert data["edges"][0]["source"] == "c1"
        assert data["edges"][0]["target"] == "c2"


class _TenantFilterStorage:
    async def list_calls(self, limit=100, offset=0, **kw):
        org_id = kw.get("org_id")
        tenant_id = kw.get("tenant_id")
        all_calls = [
            {"id": "a", "trace_id": "t1", "tool_name": "a", "duration_ms": 1, "success": True, "org_id": "org1", "tenant_id": "tnt1"},
            {"id": "b", "trace_id": "t1", "tool_name": "b", "duration_ms": 2, "success": True, "org_id": "org2", "tenant_id": "tnt1"},
        ]
        if org_id:
            all_calls = [c for c in all_calls if c.get("org_id") == org_id]
        if tenant_id:
            all_calls = [c for c in all_calls if c.get("tenant_id") == tenant_id]
        return all_calls[offset:offset + limit]
    async def get_call_stats(self):
        return {"total_calls": 2, "successful_calls": 2, "avg_latency_ms": 1.5, "top_tools": []}
    async def get_call(self, call_id):
        return None


@pytest.mark.asyncio
async def test_analytics_calls_tenant_filter():
    app = create_app()
    app.dependency_overrides[get_storage] = lambda: _TenantFilterStorage()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/analytics/calls", params={"org_id": "org1"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["org_id"] == "org1"

        resp2 = await ac.get("/api/analytics/calls", params={"tenant_id": "tnt1"})
        assert resp2.status_code == 200
        assert len(resp2.json()) == 2
