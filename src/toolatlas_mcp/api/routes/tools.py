import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query

from toolatlas_mcp.api.schemas import ToolResponse, ToolTestRequest, ToolTestResponse, ToolUpdate
from toolatlas_mcp.db import get_storage
from toolatlas_mcp.registry.mcp_client import MCPClient
from toolatlas_mcp.registry.storage import StorageBackend

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("")
async def list_tools(
    server_id: str | None = Query(None),
    domain: str | None = Query(None),
    search: str | None = Query(None),
    storage: StorageBackend = Depends(get_storage),
):
    tools = await storage.list_tools(server_id=server_id)

    if domain:
        tools = [t for t in tools if domain in (t.get("domain", []) if isinstance(t.get("domain"), list) else [t.get("domain")])]
    if search:
        search_lower = search.lower()
        tools = [
            t for t in tools
            if search_lower in t.get("name", "").lower() or search_lower in t.get("description", "").lower()
        ]

    result = []
    for t in tools:
        server = await storage.get_server(t.get("server_id", ""))
        result.append(ToolResponse(
            id=t.get("id", ""),
            server_id=t.get("server_id", ""),
            name=t.get("name", ""),
            original_name=t.get("original_name", ""),
            original_description=t.get("original_description"),
            description=t.get("description", ""),
            input_schema=t.get("input_schema", {}),
            enabled=t.get("enabled", True),
            tags=t.get("tags", []),
            domain=t.get("domain", []),
            glossary_term_ids=t.get("glossary_term_ids", []),
            server_name=server.get("name") if server else None,
        ))
    return result


@router.get("/{tool_id}")
async def get_tool(tool_id: str, storage: StorageBackend = Depends(get_storage)):
    tool = await storage.get_tool(tool_id)
    if not tool:
        raise HTTPException(404, "Tool not found")
    server = await storage.get_server(tool.get("server_id", ""))
    return ToolResponse(
        id=tool.get("id", ""),
        server_id=tool.get("server_id", ""),
        name=tool.get("name", ""),
        original_name=tool.get("original_name", ""),
        original_description=tool.get("original_description"),
        description=tool.get("description", ""),
        input_schema=tool.get("input_schema", {}),
        enabled=tool.get("enabled", True),
        tags=tool.get("tags", []),
        domain=tool.get("domain", []),
        glossary_term_ids=tool.get("glossary_term_ids", []),
        server_name=server.get("name") if server else None,
    )


@router.patch("/{tool_id}")
async def update_tool(tool_id: str, body: ToolUpdate, storage: StorageBackend = Depends(get_storage)):
    kwargs = body.model_dump(exclude_unset=True)
    tool = await storage.update_tool(tool_id, **kwargs)
    if not tool:
        raise HTTPException(404, "Tool not found")
    server = await storage.get_server(tool.get("server_id", ""))
    return ToolResponse(
        id=tool.get("id", ""),
        server_id=tool.get("server_id", ""),
        name=tool.get("name", ""),
        original_name=tool.get("original_name", ""),
        original_description=tool.get("original_description"),
        description=tool.get("description", ""),
        input_schema=tool.get("input_schema", {}),
        enabled=tool.get("enabled", True),
        tags=tool.get("tags", []),
        domain=tool.get("domain", []),
        glossary_term_ids=tool.get("glossary_term_ids", []),
        server_name=server.get("name") if server else None,
    )


@router.delete("/{tool_id}")
async def delete_tool(tool_id: str, storage: StorageBackend = Depends(get_storage)):
    deleted = await storage.delete_tool(tool_id)
    if not deleted:
        raise HTTPException(404, "Tool not found")
    return {"ok": True}


@router.post("/{tool_id}/test")
async def test_tool(tool_id: str, body: ToolTestRequest, storage: StorageBackend = Depends(get_storage)):
    tool = await storage.get_tool(tool_id)
    if not tool:
        raise HTTPException(404, "Tool not found")
    server = await storage.get_server(tool.get("server_id", ""))
    if not server:
        raise HTTPException(404, "Server not found for this tool")

    client = MCPClient(transport=server.get("transport", "sse"), command=server.get("command"), url=server.get("url"))
    start = time.monotonic()
    try:
        await client.connect()
        await client.initialize()
        result = await client.call_tool(tool.get("name", ""), body.arguments)
        duration_ms = (time.monotonic() - start) * 1000
        return ToolTestResponse(name=tool.get("name", ""), result=result, duration_ms=round(duration_ms, 2))
    except Exception as e:
        duration_ms = (time.monotonic() - start) * 1000
        log.warning("Tool test failed for '%s': %s", tool.get("name"), e)
        return ToolTestResponse(name=tool.get("name", ""), error=str(e), duration_ms=round(duration_ms, 2))
    finally:
        await client.close()
