from fastapi import APIRouter, Depends, Query

from toolatlas_mcp.api.schemas import SearchResult
from toolatlas_mcp.db import get_storage
from toolatlas_mcp.registry.storage import StorageBackend

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def search_all(q: str = Query("", min_length=1), storage: StorageBackend = Depends(get_storage)):
    q = q.lower()
    result = SearchResult()

    servers = await storage.list_servers()
    result.servers = [s for s in servers if q in s.get("name", "").lower()]

    tools = await storage.list_tools()
    result.tools = [t for t in tools if q in t.get("name", "").lower() or q in t.get("description", "").lower()]

    proxies = await storage.list_proxies()
    result.proxies = [p for p in proxies if q in p.get("name", "").lower() or q in p.get("slug", "").lower()]

    terms = await storage.list_glossary_terms()
    result.glossary_terms = [g for g in terms if q in g.get("term", "").lower() or q in g.get("definition", "").lower()]

    return result
