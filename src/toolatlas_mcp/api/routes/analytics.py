from fastapi import APIRouter, Depends, HTTPException, Query

from toolatlas_mcp.api.schemas import CallDetailResponse, CallRecordResponse, CallStatsResponse
from toolatlas_mcp.db import get_storage
from toolatlas_mcp.registry.storage import StorageBackend

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/stats")
async def get_stats(storage: StorageBackend = Depends(get_storage)):
    stats = await storage.get_call_stats()
    return CallStatsResponse(**stats)


@router.get("/calls")
async def list_calls(
    proxy_id: str | None = Query(None),
    tool_id: str | None = Query(None),
    org_id: str | None = Query(None),
    tenant_id: str | None = Query(None),
    limit: int = Query(100),
    offset: int = Query(0),
    storage: StorageBackend = Depends(get_storage),
):
    calls = await storage.list_calls(
        proxy_id=proxy_id,
        tool_id=tool_id,
        org_id=org_id,
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
    )
    return [CallRecordResponse(**c) for c in calls]


@router.get("/calls/{call_id}")
async def get_call_detail(call_id: str, storage: StorageBackend = Depends(get_storage)):
    call = await storage.get_call(call_id)
    if not call:
        raise HTTPException(404, "Call not found")
    return CallDetailResponse(**call)


@router.get("/top-tools")
async def top_tools(limit: int = Query(20), storage: StorageBackend = Depends(get_storage)):
    stats = await storage.get_call_stats()
    return stats.get("top_tools", [])[:limit]


@router.get("/slowest-tools")
async def slowest_tools(limit: int = Query(20), storage: StorageBackend = Depends(get_storage)):
    calls = await storage.list_calls(limit=10000)
    agg: dict[str, list[float]] = {}
    for c in calls:
        name = c.get("tool_name", "?")
        dur = c.get("duration_ms", 0)
        if name not in agg:
            agg[name] = []
        agg[name].append(dur)
    averages = [(name, sum(durs) / len(durs)) for name, durs in agg.items()]
    averages.sort(key=lambda x: -x[1])
    return [{"name": name, "avg_latency_ms": round(avg, 2)} for name, avg in averages[:limit]]


@router.get("/error-rates")
async def error_rates(storage: StorageBackend = Depends(get_storage)):
    calls = await storage.list_calls(limit=10000)
    total = len(calls)
    if total == 0:
        return {"total": 0, "error_count": 0, "error_rate": 0}

    errors = sum(1 for c in calls if not c.get("success", True))
    return {
        "total": total,
        "error_count": errors,
        "error_rate": round(errors / total * 100, 2),
    }
