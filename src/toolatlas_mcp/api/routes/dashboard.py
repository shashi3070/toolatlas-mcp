from fastapi import APIRouter, Depends

from toolatlas_mcp.api.schemas import DashboardSummaryResponse
from toolatlas_mcp.db import get_storage
from toolatlas_mcp.registry.storage import StorageBackend
from toolatlas_mcp.services.ws_manager import ws_manager

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(storage: StorageBackend = Depends(get_storage)):
    servers_counts = await storage.count_servers()
    total_proxies = await storage.count_proxies()
    total_tools = await storage.count_tools()
    stats = await storage.get_call_stats()

    return DashboardSummaryResponse(
        servers={
            "total": servers_counts["total"],
            "connected": servers_counts["connected"],
            "disconnected": servers_counts["disconnected"],
            "unknown": servers_counts["unknown"],
            "total_tools": total_tools,
        },
        proxies={"total": total_proxies},
        tools={"total": total_tools},
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
