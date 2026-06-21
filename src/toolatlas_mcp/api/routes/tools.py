from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from toolatlas_mcp.api.schemas import ToolResponse, ToolUpdate
from toolatlas_mcp.db import get_db
from toolatlas_mcp.registry.repository import RegistryRepository

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("")
async def list_tools(
    server_id: str | None = Query(None),
    domain: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    repo = RegistryRepository(db)
    tools = await repo.list_tools(server_id=server_id)

    if domain:
        tools = [t for t in tools if t.domain and (domain in (t.domain if isinstance(t.domain, list) else [t.domain]))]
    if search:
        search_lower = search.lower()
        tools = [
            t for t in tools
            if search_lower in t.name.lower() or search_lower in t.description.lower()
        ]

    result = []
    for t in tools:
        server = await repo.get_server(t.server_id)
        result.append(ToolResponse(
            id=t.id,
            server_id=t.server_id,
            name=t.name,
            original_name=t.original_name,
            original_description=t.original_description,
            description=t.description,
            input_schema=t.input_schema,
            enabled=t.enabled,
            tags=t.tags,
            domain=t.domain,
            glossary_term_id=t.glossary_term_id,
            server_name=server.name if server else None,
        ))
    return result


@router.get("/{tool_id}")
async def get_tool(tool_id: str, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    tool = await repo.get_tool(tool_id)
    if not tool:
        raise HTTPException(404, "Tool not found")
    server = await repo.get_server(tool.server_id)
    return ToolResponse(
        id=tool.id,
        server_id=tool.server_id,
        name=tool.name,
        original_name=tool.original_name,
        original_description=tool.original_description,
        description=tool.description,
        input_schema=tool.input_schema,
        enabled=tool.enabled,
        tags=tool.tags,
        domain=tool.domain,
        glossary_term_id=tool.glossary_term_id,
        server_name=server.name if server else None,
    )


@router.patch("/{tool_id}")
async def update_tool(tool_id: str, body: ToolUpdate, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    kwargs = body.model_dump(exclude_unset=True)
    tool = await repo.update_tool(tool_id, **kwargs)
    if not tool:
        raise HTTPException(404, "Tool not found")
    server = await repo.get_server(tool.server_id)
    return ToolResponse(
        id=tool.id,
        server_id=tool.server_id,
        name=tool.name,
        original_name=tool.original_name,
        original_description=tool.original_description,
        description=tool.description,
        input_schema=tool.input_schema,
        enabled=tool.enabled,
        tags=tool.tags,
        domain=tool.domain,
        glossary_term_id=tool.glossary_term_id,
        server_name=server.name if server else None,
    )


@router.delete("/{tool_id}")
async def delete_tool(tool_id: str, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    deleted = await repo.delete_tool(tool_id)
    if not deleted:
        raise HTTPException(404, "Tool not found")
    return {"ok": True}
