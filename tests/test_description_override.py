import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_custom_tool_description(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    dev_proxy = [p for p in resp.json() if p["slug"] == "dev"][0]

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    tools = resp.json()
    if not tools:
        pytest.skip("No tools found")
    tool = tools[0]

    custom_desc = "Custom description set via proxy tool setting"
    resp = await seeded_client.patch(
        f"/api/proxies/{dev_proxy['id']}/tools/{tool['id']}",
        json={"custom_description": custom_desc},
    )
    assert resp.status_code == 200
    assert resp.json()["custom_description"] == custom_desc


@pytest.mark.asyncio
async def test_tool_alias(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    dev_proxy = [p for p in resp.json() if p["slug"] == "dev"][0]

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    tools = resp.json()
    if not tools:
        pytest.skip("No tools found")
    tool = tools[0]

    resp = await seeded_client.patch(
        f"/api/proxies/{dev_proxy['id']}/tools/{tool['id']}",
        json={"alias": "my-custom-name"},
    )
    assert resp.status_code == 200
    assert resp.json()["alias"] == "my-custom-name"
