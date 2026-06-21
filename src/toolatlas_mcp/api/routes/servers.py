import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from toolatlas_mcp.api.schemas import DiscoverPreviewRequest, ServerCreate, ServerResponse, ServerUpdate, ToolResponse
from toolatlas_mcp.db import get_db
from toolatlas_mcp.registry.mcp_client import MCPClient
from toolatlas_mcp.registry.repository import RegistryRepository

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/servers", tags=["servers"])


@router.get("")
async def list_servers(db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    servers = await repo.list_servers()
    return [ServerResponse.model_validate(s) for s in servers]


@router.post("", status_code=201)
async def create_server(body: ServerCreate, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    server = await repo.create_server(
        name=body.name,
        transport=body.transport,
        command=body.command,
        url=body.url,
    )
    return ServerResponse.model_validate(server)


@router.get("/{server_id}")
async def get_server(server_id: str, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    server = await repo.get_server(server_id)
    if not server:
        raise HTTPException(404, "Server not found")
    return ServerResponse.model_validate(server)


@router.patch("/{server_id}")
async def update_server(server_id: str, body: ServerUpdate, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    kwargs = body.model_dump(exclude_unset=True)
    server = await repo.update_server(server_id, **kwargs)
    if not server:
        raise HTTPException(404, "Server not found")
    return ServerResponse.model_validate(server)


@router.delete("/{server_id}")
async def delete_server(server_id: str, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    deleted = await repo.delete_server(server_id)
    if not deleted:
        raise HTTPException(404, "Server not found")
    return {"ok": True}


@router.post("/discover-preview")
async def discover_preview(body: DiscoverPreviewRequest):
    client = MCPClient(transport=body.transport, command=body.command, url=body.url)
    try:
        await client.connect()
        await client.initialize()
        remote_tools = await client.list_tools()
    except Exception as e:
        raise HTTPException(502, f"Failed to connect: {e}")
    finally:
        await client.close()

    return [
        {
            "name": rt.get("name", ""),
            "description": rt.get("description", ""),
            "input_schema": rt.get("inputSchema", {}),
        }
        for rt in remote_tools
    ]


@router.post("/{server_id}/discover")
async def discover_server_tools(server_id: str, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    server = await repo.get_server(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    client = MCPClient(transport=server.transport, command=server.command, url=server.url)
    try:
        await client.connect()
        await client.initialize()
        remote_tools = await client.list_tools()
    except Exception as e:
        log.warning("Failed to discover tools from '%s': %s", server.name, e)
        raise HTTPException(502, f"Failed to connect to server: {e}")
    finally:
        await client.close()

    discovered = []
    for rt in remote_tools:
        tool = await repo.upsert_tool(
            server_id=server.id,
            name=rt.get("name", ""),
            description=rt.get("description", ""),
            input_schema=rt.get("inputSchema", {}),
        )
        discovered.append(tool)

    server_tools = await repo.list_tools(server_id=server.id)
    return [ToolResponse.model_validate(t) for t in server_tools]
