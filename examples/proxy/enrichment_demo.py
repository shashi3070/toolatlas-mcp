"""Enrichment Demo

Demonstrates creating glossary terms and domains, linking them to tools,
and verifying the enriched descriptions via the REST API.

Requires a running ToolAtlas instance.

Usage:
    python examples/proxy/enrichment_demo.py
"""

import httpx
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


async def main():
    client = httpx.AsyncClient(base_url=BASE_URL)

    # 1. Create a domain
    resp = await client.post("/api/glossary/domains", json={
        "name": "DevOps",
        "description": "Infrastructure and deployment tools",
    })
    if resp.status_code == 201:
        domain_id = resp.json()["id"]
        log.info("Created domain: DevOps")
    else:
        resp = await client.get("/api/glossary/domains")
        domain_id = resp.json()[0]["id"]
        log.info("Domain already exists")

    # 2. Create glossary terms
    terms = [
        {"term": "S3", "definition": "Amazon Simple Storage Service — object storage"},
        {"term": "EC2", "definition": "Amazon Elastic Compute Cloud — virtual servers"},
        {"term": "Lambda", "definition": "AWS Lambda — serverless compute"},
    ]
    for t in terms:
        resp = await client.post("/api/glossary/terms", json={
            "domain_id": domain_id, "term": t["term"], "definition": t["definition"],
        })
        if resp.status_code == 201:
            log.info("Created term: %s", t["term"])

    # 3. List servers and find AWS
    resp = await client.get("/api/servers")
    servers = resp.json()
    aws = next((s for s in servers if s["name"] == "AWS"), None)
    if not aws:
        log.warning("AWS server not found — create it first")
        return

    # 4. Link AWS server to a proxy
    resp = await client.get("/api/proxies")
    devops_proxy = next((p for p in resp.json() if p["slug"] == "devops"), None)
    if not devops_proxy:
        log.warning("devops proxy not found — create it first")
        return

    # 5. Check enriched descriptions
    resp = await client.get(f"/api/proxies/{devops_proxy['id']}/tools")
    tools = resp.json()
    for t in tools:
        log.info("Tool: %s", t["name"])
        log.info("  Description (first 200 chars): %s", t["description"][:200])
        log.info("  Tags: %s", t.get("tags", []))
        log.info("  Domains: %s", t.get("domain", []))
        log.info("  ---")

    await client.aclose()
    log.info("Enrichment demo completed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
