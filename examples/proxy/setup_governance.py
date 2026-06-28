"""Proxy Governance Example

Demonstrates creating a proxy, linking servers, disabling risky tools,
and setting aliases via the ToolAtlas REST API.

Requires a running ToolAtlas instance (http://localhost:8000).

Usage:
    python examples/proxy/setup_governance.py
"""

import httpx
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


async def main():
    client = httpx.AsyncClient(base_url=BASE_URL)

    # 1. List available servers
    resp = await client.get("/api/servers")
    resp.raise_for_status()
    servers = resp.json()
    if not servers:
        log.error("No servers found. Register servers first.")
        return
    server_map = {s["name"]: s for s in servers}
    log.info("Available servers: %s", list(server_map.keys()))

    # 2. Create a proxy
    resp = await client.post("/api/proxies", json={
        "name": "Engineering Team",
        "slug": "eng",
        "description": "Tools for the engineering team",
    })
    if resp.status_code == 400:
        log.warning("Proxy 'eng' already exists, fetching...")
        resp = await client.get("/api/proxies")
        proxies = resp.json()
        proxy_id = next(p["id"] for p in proxies if p["slug"] == "eng")
    else:
        resp.raise_for_status()
        proxy_id = resp.json()["id"]
    log.info("Proxy ID: %s", proxy_id)

    # 3. Link GitHub server
    if "GitHub" in server_map:
        resp = await client.post(f"/api/proxies/{proxy_id}/servers", json={
            "server_id": server_map["GitHub"]["id"],
        })
        resp.raise_for_status()
        log.info("Linked GitHub server")

    # 4. Get tools for the proxy
    resp = await client.get(f"/api/proxies/{proxy_id}/tools")
    tools = resp.json()
    for t in tools:
        log.info("  Tool: %s (enabled=%s, alias=%s)", t["name"], t["enabled"], t["alias"])

    # 5. Disable "delete_repo"
    delete_repo = next((t for t in tools if t["original_name"] == "delete_repo"), None)
    if delete_repo:
        resp = await client.patch(
            f"/api/proxies/{proxy_id}/tools/{delete_repo['id']}",
            json={"enabled": False},
        )
        resp.raise_for_status()
        log.info("Disabled delete_repo")

    # 6. Set an alias for "search_code"
    search_code = next((t for t in tools if t["original_name"] == "search_code"), None)
    if search_code:
        resp = await client.patch(
            f"/api/proxies/{proxy_id}/tools/{search_code['id']}",
            json={"alias": "find-code"},
        )
        resp.raise_for_status()
        log.info("Set alias: search_code -> find-code")

    # 7. Verify changes
    resp = await client.get(f"/api/proxies/{proxy_id}/tools")
    updated = resp.json()
    for t in updated:
        log.info("  After: name=%s | enabled=%s | alias=%s | original=%s",
                 t["name"], t["enabled"], t["alias"], t["original_name"])

    await client.aclose()
    log.info("Governance example completed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
