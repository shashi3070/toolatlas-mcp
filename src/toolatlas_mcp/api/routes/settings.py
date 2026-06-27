from fastapi import APIRouter

from toolatlas_mcp.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings():
    from toolatlas_mcp.proxy.server import get_cache_stats
    return {
        "host": settings.host,
        "port": settings.port,
        "database_url": settings.database_url,
        "storage_type": settings.storage_type,
        "log_level": settings.log_level,
        "is_db_backend": settings.is_db_backend,
        "cache": get_cache_stats(),
    }
