from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from toolatlas_mcp.api.schemas import CallDetailResponse, CallRecordResponse, CallStatsResponse
from toolatlas_mcp.db import get_db
from toolatlas_mcp.registry.repository import RegistryRepository

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    stats = await repo.get_call_stats()
    return CallStatsResponse(**stats)


@router.get("/calls")
async def list_calls(
    proxy_id: str | None = Query(None),
    tool_id: str | None = Query(None),
    limit: int = Query(100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    repo = RegistryRepository(db)
    calls = await repo.list_calls(
        proxy_id=proxy_id,
        tool_id=tool_id,
        limit=limit,
        offset=offset,
    )
    return [CallRecordResponse.model_validate(c) for c in calls]


@router.get("/calls/{call_id}")
async def get_call_detail(call_id: str, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    call = await repo.get_call(call_id)
    if not call:
        raise HTTPException(404, "Call not found")
    return CallDetailResponse.model_validate(call)
