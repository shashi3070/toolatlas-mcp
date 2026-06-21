import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_e2e_full_registration_flow(seeded_client: AsyncClient):
    # 1. List servers
    resp = await seeded_client.get("/api/servers")
    assert resp.status_code == 200
    servers = resp.json()
    assert len(servers) >= 6

    # 2. List proxies
    resp = await seeded_client.get("/api/proxies")
    assert resp.status_code == 200
    proxies = resp.json()
    assert len(proxies) == 3

    # 3. Check dev proxy tools
    dev_proxy = [p for p in proxies if p["slug"] == "dev"][0]
    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    assert resp.status_code == 200
    dev_tools = resp.json()

    # Should have GitHub + Jira + Confluence tools
    assert len(dev_tools) >= 6
    dev_names = [t["name"] for t in dev_tools]
    assert "search_code" in dev_names
    assert "search_issues" in dev_names
    assert "search_pages" in dev_names
    assert "delete_repo" in dev_names  # shown (blocked)
    assert [t for t in dev_tools if t["name"] == "delete_repo"][0]["enabled"] is False

    # 4. Check PM proxy tools
    pm_proxy = [p for p in proxies if p["slug"] == "pm"][0]
    resp = await seeded_client.get(f"/api/proxies/{pm_proxy['id']}/tools")
    pm_tools = resp.json()
    pm_names = [t["name"] for t in pm_tools]
    assert "search_issues" in pm_names
    assert "search_pages" in pm_names
    assert "send_message" in pm_names
    assert "search_code" not in pm_names

    # 5. Check devops proxy tools
    devops_proxy = [p for p in proxies if p["slug"] == "devops"][0]
    resp = await seeded_client.get(f"/api/proxies/{devops_proxy['id']}/tools")
    devops_tools = resp.json()
    devops_names = [t["name"] for t in devops_tools]
    assert "list_s3_buckets" in devops_names
    assert "list_incidents" in devops_names
    assert "delete_repo" in devops_names  # shown (blocked)
    assert [t for t in devops_tools if t["name"] == "delete_repo"][0]["enabled"] is False

    # 6. Update tool description
    resp = await seeded_client.get("/api/tools")
    all_tools = resp.json()
    search_code = [t for t in all_tools if t["name"] == "search_code"]
    if search_code:
        resp = await seeded_client.patch(
            f"/api/tools/{search_code[0]['id']}",
            json={"description": "Custom: Search code across all repos"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Custom: Search code across all repos"

    # 7. Check analytics
    resp = await seeded_client.get("/api/analytics/stats")
    assert resp.status_code == 200

    # 8. Check glossary
    resp = await seeded_client.get("/api/glossary/terms")
    assert resp.status_code == 200
    assert len(resp.json()) >= 5
