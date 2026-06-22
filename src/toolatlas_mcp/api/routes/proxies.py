from fastapi import APIRouter, Depends, HTTPException

from toolatlas_mcp.api.schemas import (
    ProxyCreate,
    ProxyLinkServer,
    ProxyResponse,
    ProxyStatsResponse,
    ProxyUpdate,
    ServerResponse,
    ToolResponse,
    ToolSettingUpdate,
)
from toolatlas_mcp.db import get_storage
from toolatlas_mcp.registry.storage import StorageBackend

router = APIRouter(prefix="/api/proxies", tags=["proxies"])


@router.get("")
async def list_proxies(storage: StorageBackend = Depends(get_storage)):
    proxies = await storage.list_proxies()
    return [ProxyResponse(**p) for p in proxies]


@router.post("", status_code=201)
async def create_proxy(body: ProxyCreate, storage: StorageBackend = Depends(get_storage)):
    existing = await storage.get_proxy_by_slug(body.slug)
    if existing:
        raise HTTPException(400, f"Proxy with slug '{body.slug}' already exists")
    proxy = await storage.create_proxy(
        name=body.name,
        slug=body.slug,
        description=body.description,
    )
    return ProxyResponse(**proxy)


@router.get("/{proxy_id}")
async def get_proxy(proxy_id: str, storage: StorageBackend = Depends(get_storage)):
    proxy = await storage.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    return ProxyResponse(**proxy)


@router.patch("/{proxy_id}")
async def update_proxy(proxy_id: str, body: ProxyUpdate, storage: StorageBackend = Depends(get_storage)):
    kwargs = body.model_dump(exclude_unset=True)
    if "slug" in kwargs:
        existing = await storage.get_proxy_by_slug(kwargs["slug"])
        if existing and existing.get("id") != proxy_id:
            raise HTTPException(400, f"Slug '{kwargs['slug']}' already in use")
    proxy = await storage.update_proxy(proxy_id, **kwargs)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    return ProxyResponse(**proxy)


@router.delete("/{proxy_id}")
async def delete_proxy(proxy_id: str, storage: StorageBackend = Depends(get_storage)):
    deleted = await storage.delete_proxy(proxy_id)
    if not deleted:
        raise HTTPException(404, "Proxy not found")
    return {"ok": True}


@router.get("/{proxy_id}/servers")
async def get_proxy_servers(proxy_id: str, storage: StorageBackend = Depends(get_storage)):
    proxy = await storage.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    servers = await storage.get_proxy_servers(proxy_id)
    return [ServerResponse(**s) for s in servers]


@router.post("/{proxy_id}/servers")
async def link_server(proxy_id: str, body: ProxyLinkServer, storage: StorageBackend = Depends(get_storage)):
    proxy = await storage.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    server = await storage.get_server(body.server_id)
    if not server:
        raise HTTPException(404, "Server not found")
    await storage.link_server_to_proxy(proxy_id, body.server_id, selected_tools=body.tool_names)
    if body.tool_names is not None:
        server_tools = await storage.list_tools(server_id=body.server_id)
        for t in server_tools:
            if t.get("name") not in body.tool_names:
                await storage.upsert_tool_setting(proxy_id, t.get("id", ""), enabled=False)
    return {"ok": True}


@router.delete("/{proxy_id}/servers/{server_id}")
async def unlink_server(proxy_id: str, server_id: str, storage: StorageBackend = Depends(get_storage)):
    await storage.unlink_server_from_proxy(proxy_id, server_id)
    return {"ok": True}


@router.get("/{proxy_id}/tools")
async def get_proxy_tools(proxy_id: str, storage: StorageBackend = Depends(get_storage)):
    proxy = await storage.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    servers = await storage.get_proxy_servers(proxy_id)
    tools = []
    for server in servers:
        server_tools = await storage.list_tools(server_id=server.get("id"))
        for t in server_tools:
            setting = await storage.get_tool_setting(proxy_id, t.get("id", ""))
            display_desc = setting.get("custom_description") if setting and setting.get("custom_description") else t.get("description", "")

            enrichment = []
            tags = t.get("tags", [])
            if tags:
                enrichment.append(f"Tags: {', '.join(tags)}")
            raw_domains = t.get("domain", [])
            if isinstance(raw_domains, str):
                raw_domains = [raw_domains]
            if raw_domains:
                enrichment.append(f"Domain: {', '.join(raw_domains)}")
            if t.get("glossary_term_id"):
                gt = await storage.get_glossary_term(t["glossary_term_id"])
                if gt:
                    enrichment.append(f"Glossary: {gt.get('definition') or gt.get('term')}")
            if enrichment:
                display_desc = (display_desc + "\n" + "\n".join(enrichment)) if display_desc else "\n".join(enrichment)

            tools.append(ToolResponse(
                id=t.get("id", ""),
                server_id=t.get("server_id", ""),
                name=setting.get("alias") if setting and setting.get("alias") else t.get("name", ""),
                original_name=t.get("original_name", ""),
                description=display_desc,
                input_schema=t.get("input_schema", {}),
                enabled=setting.get("enabled") if setting else t.get("enabled", True),
                tags=t.get("tags", []),
                domain=t.get("domain", []),
                glossary_term_id=t.get("glossary_term_id"),
                server_name=server.get("name"),
            ))
    return tools


@router.patch("/{proxy_id}/tools/{tool_id}")
async def update_tool_setting(
    proxy_id: str, tool_id: str, body: ToolSettingUpdate,
    storage: StorageBackend = Depends(get_storage),
):
    proxy = await storage.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    tool = await storage.get_tool(tool_id)
    if not tool:
        raise HTTPException(404, "Tool not found")
    kwargs = body.model_dump(exclude_unset=True)
    setting = await storage.upsert_tool_setting(proxy_id, tool_id, **kwargs)
    return {
        "proxy_id": proxy_id,
        "tool_id": tool_id,
        "enabled": setting.get("enabled"),
        "custom_description": setting.get("custom_description"),
        "alias": setting.get("alias"),
    }


@router.get("/{proxy_id}/stats")
async def get_proxy_stats(proxy_id: str, storage: StorageBackend = Depends(get_storage)):
    proxy = await storage.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    stats = await storage.get_proxy_stats(proxy_id)
    return ProxyStatsResponse(**stats)
