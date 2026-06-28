"""Collision Scenario Example

Creates two servers with the same-named tool, creates a proxy with both,
and verifies the collision detection produces disambiguated display names.

Requires a running ToolAtlas instance.

Usage:
    python examples/proxy/collision_scenario.py
"""

import httpx
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


async def main():
    client = httpx.AsyncClient(base_url=BASE_URL)

    # 1. Register two servers with the same tool name
    for suffix in ("A", "B"):
        resp = await client.post("/api/servers", json={
            "name": f"Search-{suffix}",
            "transport": "sse",
            "url": f"http://search-{suffix.lower()}.local:8000",
        })
        resp.raise_for_status()
        log.info("Created server Search-%s", suffix)

    # 2. List servers
    resp = await client.get("/api/servers")
    servers = resp.json()
    server_a = next(s for s in servers if s["name"] == "Search-A")
    server_b = next(s for s in servers if s["name"] == "Search-B")

    # 3. Create a proxy that links both servers
    resp = await client.post("/api/proxies", json={
        "name": "Collision Test",
        "slug": "collision-test",
        "description": "Proxy with colliding tool names",
    })

    if resp.status_code == 400:
        resp = await client.get("/api/proxies")
        proxy_id = next(p["id"] for p in resp.json() if p["slug"] == "collision-test")
    else:
        proxy_id = resp.json()["id"]

    for srv in (server_a, server_b):
        await client.post(f"/api/proxies/{proxy_id}/servers", json={
            "server_id": srv["id"],
        })
    log.info("Linked both servers to proxy")

    # 4. List proxy tools — notice the collision suffix
    resp = await client.get(f"/api/proxies/{proxy_id}/tools")
    tools = resp.json()
    log.info("Tools for collision-test proxy:")
    for t in tools:
        log.info("  display=%s | original=%s | server=%s",
                 t["name"], t["original_name"], t.get("server_name"))

    # 5. Verify disambiguation
    names = [t["name"] for t in tools]
    if any("Search-A" in n or "Search-B" in n for n in names):
        log.info("SUCCESS: Collision detected and disambiguated")
    else:
        log.warning("No collision detected — servers may not have same-named tools")

    await client.aclose()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
