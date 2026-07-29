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
    return await storage.get_tool_latency_stats(limit=limit)


@router.get("/error-rates")
async def error_rates(storage: StorageBackend = Depends(get_storage)):
    return await storage.get_error_rate()
