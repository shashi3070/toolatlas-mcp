import logging

from fastapi import APIRouter, Depends, HTTPException

from toolatlas_mcp.api.schemas import DiscoverPreviewRequest, ServerCreate, ServerResponse, ServerUpdate, ToolResponse
from toolatlas_mcp.db import get_storage
from toolatlas_mcp.registry.mcp_client import MCPClient
from toolatlas_mcp.registry.storage import StorageBackend

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/servers", tags=["servers"])


@router.get("")
async def list_servers(storage: StorageBackend = Depends(get_storage)):
    servers = await storage.list_servers()
    return [ServerResponse(**s) for s in servers]


@router.post("", status_code=201)
async def create_server(body: ServerCreate, storage: StorageBackend = Depends(get_storage)):
    server = await storage.create_server(
        name=body.name,
        transport=body.transport,
        command=body.command,
        url=body.url,
    )
    from toolatlas_mcp.services.health_checker import ping_single_server
    try:
        await ping_single_server(storage, server["id"])
    except Exception:
        pass
    updated = await storage.get_server(server["id"])
    return ServerResponse(**updated)


@router.get("/{server_id}")
async def get_server(server_id: str, storage: StorageBackend = Depends(get_storage)):
    server = await storage.get_server(server_id)
    if not server:
        raise HTTPException(404, "Server not found")
    return ServerResponse(**server)


@router.patch("/{server_id}")
async def update_server(server_id: str, body: ServerUpdate, storage: StorageBackend = Depends(get_storage)):
    kwargs = body.model_dump(exclude_unset=True)
    server = await storage.update_server(server_id, **kwargs)
    if not server:
        raise HTTPException(404, "Server not found")
    return ServerResponse(**server)


@router.delete("/{server_id}")
async def delete_server(server_id: str, storage: StorageBackend = Depends(get_storage)):
    deleted = await storage.delete_server(server_id)
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


@router.post("/{server_id}/ping")
async def ping_server(server_id: str, storage: StorageBackend = Depends(get_storage)):
    from toolatlas_mcp.services.health_checker import ping_single_server
    result = await ping_single_server(storage, server_id)
    if result is None:
        raise HTTPException(404, "Server not found")
    return result


@router.post("/{server_id}/reconnect")
async def reconnect_server(server_id: str, storage: StorageBackend = Depends(get_storage)):
    from toolatlas_mcp.registry.mcp_client import MCPClient

    server = await storage.get_server(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    transport = server.get("transport", "sse")
    command = server.get("command")
    url = server.get("url")
    name = server.get("name", "?")

    import time
    client = MCPClient(transport=transport, command=command, url=url)
    start = time.monotonic()
    try:
        await client.connect()
        await client.initialize()
        latency_ms = (time.monotonic() - start) * 1000
        await storage.update_server(
            server_id,
            connection_status="connected",
            latency_ms=round(latency_ms, 2),
            reconnect_count=0,
        )
        # Refresh the shared connection so proxies pick up the healthy client
        from toolatlas_mcp.services.connection_manager import connection_manager
        await connection_manager.remove_client(server_id)
        return {"status": "connected", "latency_ms": round(latency_ms, 2)}
    except Exception as e:
        rc = server.get("reconnect_count", 0) or 0
        await storage.update_server(
            server_id,
            connection_status="disconnected",
            reconnect_count=rc + 1,
        )
        raise HTTPException(502, f"Reconnect failed: {e}")
    finally:
        await client.close()


@router.post("/{server_id}/discover")
async def discover_server_tools(server_id: str, storage: StorageBackend = Depends(get_storage)):
    server = await storage.get_server(server_id)
    if not server:
        raise HTTPException(404, "Server not found")

    from toolatlas_mcp.services.connection_manager import connection_manager
    try:
        client = await connection_manager.get_client(server)
        remote_tools = await client.list_tools()
    except Exception as e:
        log.warning("Failed to discover tools from '%s': %s", server["name"], e)
        raise HTTPException(502, f"Failed to connect to server: {e}")

    for rt in remote_tools:
        await storage.upsert_tool(
            server_id=server["id"],
            name=rt.get("name", ""),
            description=rt.get("description", ""),
            input_schema=rt.get("inputSchema", {}),
        )

    from datetime import datetime, timezone
    await storage.update_server(
        server["id"],
        connection_status="connected",
        last_tool_sync=datetime.now(timezone.utc),
    )

    server_tools = await storage.list_tools(server_id=server["id"])
    return [ToolResponse(**t) for t in server_tools]
