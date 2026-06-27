import asyncio
import logging
import time
from datetime import datetime, timezone

from toolatlas_mcp.config import settings
from toolatlas_mcp.registry.mcp_client import MCPClient
from toolatlas_mcp.registry.storage import StorageBackend
from toolatlas_mcp.services.ws_manager import ws_manager

log = logging.getLogger(__name__)

_PING_INTERVAL = 30.0


async def _ping_server(storage: StorageBackend, server: dict) -> dict | None:
    server_id = server.get("id")
    transport = server.get("transport", "sse")
    command = server.get("command")
    url = server.get("url")
    name = server.get("name", "?")

    client = MCPClient(transport=transport, command=command, url=url)
    start = time.monotonic()
    try:
        await client.connect()
        await client.initialize()
        latency_ms = (time.monotonic() - start) * 1000
        now = datetime.now(timezone.utc)

        await storage.update_server(
            server_id,
            connection_status="connected",
            latency_ms=round(latency_ms, 2),
            reconnect_count=0,
            last_heartbeat=now,
        )
        log.debug("Heartbeat OK  %s  %.0fms", name, latency_ms)
        return {"id": server_id, "status": "connected", "latency_ms": latency_ms}
    except Exception as e:
        log.warning("Heartbeat FAIL %s: %s", name, e)
        server_data = await storage.get_server(server_id)
        rc = (server_data or {}).get("reconnect_count", 0) or 0
        await storage.update_server(
            server_id,
            connection_status="disconnected",
            reconnect_count=rc + 1,
        )
        return {"id": server_id, "status": "disconnected", "error": str(e)}
    finally:
        await client.close()


async def health_check_loop(storage: StorageBackend):
    while True:
        try:
            servers = await storage.list_servers()
            results = []
            for server in servers:
                if not server.get("enabled", True):
                    continue
                result = await _ping_server(storage, server)
                if result:
                    results.append(result)

            connected = sum(1 for r in results if r.get("status") == "connected")
            disconnected = sum(1 for r in results if r.get("status") == "disconnected")
            log.info(
                "Health check complete: %d/%d connected",
                connected, connected + disconnected,
            )

            if results:
                await ws_manager.broadcast("server.status", {
                    "servers": results,
                    "connected": connected,
                    "disconnected": disconnected,
                    "total": len(servers),
                })
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("Health check error: %s", e)

        await asyncio.sleep(_PING_INTERVAL)


async def ping_single_server(storage: StorageBackend, server_id: str) -> dict | None:
    server = await storage.get_server(server_id)
    if not server:
        return None
    return await _ping_server(storage, server)
