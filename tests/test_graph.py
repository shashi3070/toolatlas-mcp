import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_graph_topology(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0
    types = {n["type"] for n in data["nodes"]}
    assert "proxy" in types
    assert "server" in types
    assert "tool" in types


@pytest.mark.asyncio
async def test_proxy_graph_topology(seeded_client: AsyncClient):
    proxies = (await seeded_client.get("/api/proxies")).json()
    if not proxies:
        pytest.skip("No proxies found")

    resp = await seeded_client.get(f"/api/graph/proxy/{proxies[0]['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["nodes"]) > 0


@pytest.mark.asyncio
async def test_proxy_graph_not_found(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/graph/proxy/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_traces_empty(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/graph/traces")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_traces_with_limit(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/graph/traces?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) <= 10


@pytest.mark.asyncio
async def test_trace_detail_not_found(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/graph/trace/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_co_occurrence_empty(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/graph/co-occurrence")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


@pytest.mark.asyncio
async def test_co_occurrence_with_filters(seeded_client: AsyncClient):
    proxies = (await seeded_client.get("/api/proxies")).json()
    if not proxies:
        pytest.skip("No proxies found")

    resp = await seeded_client.get(
        f"/api/graph/co-occurrence?proxy_id={proxies[0]['id']}&min_count=1&limit=20"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data


@pytest.mark.asyncio
async def test_graph_traces_proxy_filter(seeded_client: AsyncClient):
    proxies = (await seeded_client.get("/api/proxies")).json()
    if not proxies:
        pytest.skip("No proxies found")

    resp = await seeded_client.get(f"/api/graph/traces?proxy_id={proxies[0]['id']}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_full_graph_structure(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/graph")
    data = resp.json()
    for node in data["nodes"]:
        assert "id" in node
        assert "type" in node
        assert "name" in node
        assert node["type"] in ("proxy", "server", "tool")
    for edge in data["edges"]:
        assert "source" in edge
        assert "target" in edge
        assert "type" in edge
