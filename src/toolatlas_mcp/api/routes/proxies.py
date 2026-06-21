from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from toolatlas_mcp.api.schemas import (
    ProxyCreate,
    ProxyLinkServer,
    ProxyResponse,
    ProxyStatsResponse,
    ProxyUpdate,
    ToolSettingUpdate,
    ToolResponse,
)
from toolatlas_mcp.db import get_db
from toolatlas_mcp.registry.repository import RegistryRepository

router = APIRouter(prefix="/api/proxies", tags=["proxies"])


@router.get("")
async def list_proxies(db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    proxies = await repo.list_proxies()
    return [ProxyResponse.model_validate(p) for p in proxies]


@router.post("", status_code=201)
async def create_proxy(body: ProxyCreate, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    existing = await repo.get_proxy_by_slug(body.slug)
    if existing:
        raise HTTPException(400, f"Proxy with slug '{body.slug}' already exists")
    proxy = await repo.create_proxy(
        name=body.name,
        slug=body.slug,
        description=body.description,
    )
    return ProxyResponse.model_validate(proxy)


@router.get("/{proxy_id}")
async def get_proxy(proxy_id: str, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    proxy = await repo.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    return ProxyResponse.model_validate(proxy)


@router.patch("/{proxy_id}")
async def update_proxy(proxy_id: str, body: ProxyUpdate, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    kwargs = body.model_dump(exclude_unset=True)
    if "slug" in kwargs:
        existing = await repo.get_proxy_by_slug(kwargs["slug"])
        if existing and existing.id != proxy_id:
            raise HTTPException(400, f"Slug '{kwargs['slug']}' already in use")
    proxy = await repo.update_proxy(proxy_id, **kwargs)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    return ProxyResponse.model_validate(proxy)


@router.delete("/{proxy_id}")
async def delete_proxy(proxy_id: str, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    deleted = await repo.delete_proxy(proxy_id)
    if not deleted:
        raise HTTPException(404, "Proxy not found")
    return {"ok": True}


@router.get("/{proxy_id}/servers")
async def get_proxy_servers(proxy_id: str, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    proxy = await repo.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    servers = await repo.get_proxy_servers(proxy_id)
    from toolatlas_mcp.api.schemas import ServerResponse
    return [ServerResponse.model_validate(s) for s in servers]


@router.post("/{proxy_id}/servers")
async def link_server(proxy_id: str, body: ProxyLinkServer, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    proxy = await repo.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    server = await repo.get_server(body.server_id)
    if not server:
        raise HTTPException(404, "Server not found")
    await repo.link_server_to_proxy(proxy_id, body.server_id)
    return {"ok": True}


@router.delete("/{proxy_id}/servers/{server_id}")
async def unlink_server(proxy_id: str, server_id: str, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    await repo.unlink_server_from_proxy(proxy_id, server_id)
    return {"ok": True}


@router.get("/{proxy_id}/tools")
async def get_proxy_tools(proxy_id: str, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    proxy = await repo.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    servers = await repo.get_proxy_servers(proxy_id)
    tools = []
    for server in servers:
        server_tools = await repo.list_tools(server_id=server.id)
        for t in server_tools:
            setting = await repo.get_tool_setting(proxy_id, t.id)
            display_desc = setting.custom_description if setting and setting.custom_description else t.description

            enrichment = []
            if t.tags:
                enrichment.append(f"Tags: {', '.join(t.tags)}")
            raw_domains = t.domain or []
            if isinstance(raw_domains, str):
                raw_domains = [raw_domains]
            if raw_domains:
                enrichment.append(f"Domain: {', '.join(raw_domains)}")
            if t.glossary_term_id:
                gt = await repo.get_glossary_term(t.glossary_term_id)
                if gt:
                    enrichment.append(f"Glossary: {gt.definition or gt.term}")
            if enrichment:
                display_desc = (display_desc + "\n" + "\n".join(enrichment)) if display_desc else "\n".join(enrichment)

            tools.append(ToolResponse(
                id=t.id,
                server_id=t.server_id,
                name=setting.alias if setting and setting.alias else t.name,
                original_name=t.original_name,
                description=display_desc,
                input_schema=t.input_schema,
                enabled=setting.enabled if setting else t.enabled,
                tags=t.tags,
                domain=t.domain,
                glossary_term_id=t.glossary_term_id,
                server_name=server.name,
            ))
    return tools


@router.patch("/{proxy_id}/tools/{tool_id}")
async def update_tool_setting(
    proxy_id: str, tool_id: str, body: ToolSettingUpdate,
    db: AsyncSession = Depends(get_db),
):
    repo = RegistryRepository(db)
    proxy = await repo.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    tool = await repo.get_tool(tool_id)
    if not tool:
        raise HTTPException(404, "Tool not found")
    kwargs = body.model_dump(exclude_unset=True)
    setting = await repo.upsert_tool_setting(proxy_id, tool_id, **kwargs)
    return {
        "proxy_id": proxy_id,
        "tool_id": tool_id,
        "enabled": setting.enabled,
        "custom_description": setting.custom_description,
        "alias": setting.alias,
    }


@router.get("/{proxy_id}/stats")
async def get_proxy_stats(proxy_id: str, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    proxy = await repo.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    stats = await repo.get_proxy_stats(proxy_id)
    return ProxyStatsResponse(**stats)
