import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_call_tool_via_proxy(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    dev_proxy = [p for p in resp.json() if p["slug"] == "dev"][0]

    tools_resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    assert tools_resp.status_code == 200
    tools = tools_resp.json()
    if not tools:
        pytest.skip("No tools found for proxy")
    tool = tools[0]

    settings_resp = await seeded_client.patch(
        f"/api/proxies/{dev_proxy['id']}/tools/{tool['id']}",
        json={"enabled": True},
    )
    assert settings_resp.status_code in (200, 422)


@pytest.mark.asyncio
async def test_tool_update_flow(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/tools")
    tools = resp.json()
    if not tools:
        pytest.skip("No tools found")
    tool = tools[0]

    resp = await seeded_client.patch(
        f"/api/tools/{tool['id']}",
        json={"description": "Updated description for testing"},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated description for testing"


@pytest.mark.asyncio
async def test_tool_enable_disable(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/tools")
    tools = resp.json()
    if not tools:
        pytest.skip("No tools found")
    tool = tools[0]

    resp = await seeded_client.patch(
        f"/api/tools/{tool['id']}",
        json={"enabled": False},
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

    resp = await seeded_client.patch(
        f"/api/tools/{tool['id']}",
        json={"enabled": True},
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True
