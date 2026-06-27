from fastapi import APIRouter, Depends

from toolatlas_mcp.api.schemas import DashboardSummaryResponse
from toolatlas_mcp.db import get_storage
from toolatlas_mcp.registry.storage import StorageBackend
from toolatlas_mcp.services.ws_manager import ws_manager

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(storage: StorageBackend = Depends(get_storage)):
    servers = await storage.list_servers()
    proxies = await storage.list_proxies()
    tools = await storage.list_tools()
    stats = await storage.get_call_stats()

    total_servers = len(servers)
    connected = sum(1 for s in servers if s.get("connection_status") == "connected")
    disconnected = sum(1 for s in servers if s.get("connection_status") == "disconnected")
    unknown = total_servers - connected - disconnected

    return DashboardSummaryResponse(
        servers={
            "total": total_servers,
            "connected": connected,
            "disconnected": disconnected,
            "unknown": unknown,
            "total_tools": len(tools),
        },
        proxies={"total": len(proxies)},
        tools={"total": len(tools)},
        calls={
            "per_minute": stats.get("calls_per_minute", 0),
            "total": stats.get("total_calls", 0),
        },
        latency={"avg_ms": stats.get("avg_latency_ms", 0)},
        cache={
            "hit_rate": 0,
            "entries": 0,
        },
        recent_alerts=[],
        recent_activity=[],
    )


@router.get("/ws-stats")
async def ws_stats():
    return {"clients": ws_manager.client_count}
