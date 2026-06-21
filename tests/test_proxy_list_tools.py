import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_proxies(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    slugs = [p["slug"] for p in data]
    assert "dev" in slugs
    assert "pm" in slugs
    assert "devops" in slugs


@pytest.mark.asyncio
async def test_get_proxy(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    proxy_id = resp.json()[0]["id"]

    resp = await seeded_client.get(f"/api/proxies/{proxy_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == proxy_id


@pytest.mark.asyncio
async def test_get_proxy_servers(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    proxies = resp.json()
    dev_proxy = [p for p in proxies if p["slug"] == "dev"][0]

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/servers")
    assert resp.status_code == 200
    servers = resp.json()
    assert len(servers) == 3


@pytest.mark.asyncio
async def test_proxy_tools(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    dev_proxy = [p for p in resp.json() if p["slug"] == "dev"][0]

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    assert resp.status_code == 200
    tools = resp.json()
    assert len(tools) > 0


@pytest.mark.asyncio
async def test_proxy_tools_dev_blocked_delete_repo(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    dev_proxy = [p for p in resp.json() if p["slug"] == "dev"][0]

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    tools = resp.json()
    tool_map = {t["name"]: t for t in tools}
    assert "delete_repo" in tool_map
    assert tool_map["delete_repo"]["enabled"] is False


@pytest.mark.asyncio
async def test_proxy_tools_pm_has_jira_confluence_slack(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    pm_proxy = [p for p in resp.json() if p["slug"] == "pm"][0]

    resp = await seeded_client.get(f"/api/proxies/{pm_proxy['id']}/tools")
    tools = resp.json()
    tool_names = [t["name"] for t in tools]
    assert "search_issues" in tool_names
    assert "search_pages" in tool_names
    assert "send_message" in tool_names
    assert "search_code" not in tool_names


@pytest.mark.asyncio
async def test_proxy_tools_devops_has_aws_pagerduty(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    devops_proxy = [p for p in resp.json() if p["slug"] == "devops"][0]

    resp = await seeded_client.get(f"/api/proxies/{devops_proxy['id']}/tools")
    tools = resp.json()
    tool_names = [t["name"] for t in tools]
    tool_map = {t["name"]: t for t in tools}
    assert "list_s3_buckets" in tool_names
    assert "list_incidents" in tool_names
    assert "delete_repo" in tool_names  # blocked, but shown
    assert tool_map["delete_repo"]["enabled"] is False
