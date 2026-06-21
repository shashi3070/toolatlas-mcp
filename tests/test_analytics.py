import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_stats(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/analytics/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_calls" in data
    assert "successful_calls" in data
    assert "avg_latency_ms" in data


@pytest.mark.asyncio
async def test_list_calls(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/analytics/calls")
    assert resp.status_code == 200
    calls = resp.json()
    assert isinstance(calls, list)


@pytest.mark.asyncio
async def test_proxy_stats(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    proxies = resp.json()
    if not proxies:
        pytest.skip("No proxies found")

    resp = await seeded_client.get(f"/api/proxies/{proxies[0]['id']}/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_calls" in data
    assert "recent_calls" in data


@pytest.mark.asyncio
async def test_health(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
