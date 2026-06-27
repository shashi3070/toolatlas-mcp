import asyncio
import json
import logging
import random
import time
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from toolatlas_mcp import __version__
from toolatlas_mcp.db import get_storage
from toolatlas_mcp.plugin.manager import plugin_manager
from toolatlas_mcp.proxy.engine import ProxyEngine
from toolatlas_mcp.services.connection_manager import connection_manager

log = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Per-proxy state
# ---------------------------------------------------------------------------
_session_queues: dict[str, asyncio.Queue] = {}
_engines: dict[str, ProxyEngine] = {}
_engine_locks: dict[str, asyncio.Lock] = {}

# ---------------------------------------------------------------------------
# Tools cache (per-slug, TTL-based with jitter + stats)
# ---------------------------------------------------------------------------
_TOOLS_CACHE_TTL = 60
_TOOLS_CACHE_JITTER = 5
_tools_cache: dict[str, tuple[float, list]] = {}
_cache_hits = 0
_cache_misses = 0


def _cache_key(slug: str) -> str:
    return slug


def _is_cache_expired(cached: tuple[float, list] | None) -> bool:
    if cached is None:
        return True
    ttl = _TOOLS_CACHE_TTL + random.uniform(-_TOOLS_CACHE_JITTER, _TOOLS_CACHE_JITTER)
    return time.time() - cached[0] > ttl


def get_cache_stats() -> dict:
    total = _cache_hits + _cache_misses
    return {
        "hits": _cache_hits,
        "misses": _cache_misses,
        "hit_ratio": round(_cache_hits / total, 4) if total else 0.0,
    }


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _send_to_session(session_id: str, response: dict):
    q = _session_queues.get(session_id)
    if q is None:
        return
    try:
        q.put_nowait(response)
    except asyncio.QueueFull:
        log.warning("Session %s queue full, dropping response", session_id)


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------

def invalidate_proxy_cache(slug: str):
    """Remove the tools cache for *slug*.  Does NOT close shared connections."""
    _tools_cache.pop(slug, None)
    asyncio.ensure_future(plugin_manager.execute("on_cache_invalidated", slug=slug))


def invalidate_all_proxy_caches():
    _tools_cache.clear()


async def invalidate_proxies_for_server(server_id: str, storage=None):
    """Find every proxy linked to *server_id* and invalidate its tool cache."""
    # If no storage is available we clear the whole cache (safe but less precise).
    if storage is None:
        invalidate_all_proxy_caches()
        return
    try:
        proxies = await storage.list_proxies()
        for proxy in proxies:
            servers = await storage.get_proxy_servers(proxy["id"])
            if any(s["id"] == server_id for s in servers):
                _tools_cache.pop(proxy.get("slug", proxy["id"]), None)
    except Exception:
        invalidate_all_proxy_caches()


# ---------------------------------------------------------------------------
# Engine lifecycle
# ---------------------------------------------------------------------------

async def _get_engine(slug: str, storage) -> ProxyEngine:
    if slug not in _engine_locks:
        _engine_locks[slug] = asyncio.Lock()
    async with _engine_locks[slug]:
        if slug in _engines:
            engine = _engines[slug]
            engine.storage = storage
            engine.middleware.storage = storage
            return engine
        engine = ProxyEngine(storage)
        await engine.initialize_proxy(slug)
        _engines[slug] = engine
        return engine


async def _warmup_single_proxy(slug: str, storage):
    """Warm up a single proxy's cache."""
    try:
        engine = await _get_engine(slug, storage)
        tools = await engine.list_tools(slug)
        _tools_cache[slug] = (time.time(), tools)
        log.info("Warmed cache for proxy '%s' (%d tools)", slug, len(tools))
    except Exception as e:
        log.debug("Cache warmup skipped for '%s': %s", slug, e)


async def warmup_proxy_caches(storage):
    """Pre-populate tool caches for all active proxies concurrently."""
    try:
        proxies = await storage.list_proxies()
    except Exception:
        return
    tasks = [_warmup_single_proxy(p["slug"], storage) for p in proxies]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


# ---------------------------------------------------------------------------
# MCP Proxy endpoints
# ---------------------------------------------------------------------------

@router.get("/proxy/{slug}/sse")
async def proxy_sse(slug: str, request: Request):
    session_id = str(uuid.uuid4())
    q: asyncio.Queue = asyncio.Queue()
    _session_queues[session_id] = q

    async def event_generator():
        base = request.scope.get("root_path", "") or ""
        message_url = f"{base}/proxy/{slug}/message/{session_id}"
        yield {"event": "endpoint", "data": message_url}

        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    response = await asyncio.wait_for(q.get(), timeout=0.5)
                    yield {"event": "message", "data": json.dumps(response)}
                except asyncio.TimeoutError:
                    pass
        finally:
            _session_queues.pop(session_id, None)

    return EventSourceResponse(event_generator())


@router.post("/proxy/{slug}/message/{session_id}")
async def proxy_message(slug: str, session_id: str, request: Request):
    global _cache_hits, _cache_misses

    try:
        body = await request.json()
    except Exception as e:
        log.exception("Failed to parse request body")
        return JSONResponse({"ok": True}, status_code=202)

    method = body.get("method", "")
    msg_id = body.get("id")

    def send_error(code: int, message: str):
        if msg_id is not None:
            _send_to_session(
                session_id,
                {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}},
            )

    async for storage in get_storage():
        try:
            engine = await _get_engine(slug, storage)
        except Exception as e:
            log.exception("Failed to get engine for %s", slug)
            send_error(-32603, str(e))
            return JSONResponse({"ok": True}, status_code=202)

        try:
            if method in ("initialize",):
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "toolatlas-mcp", "version": __version__},
                }
                _send_to_session(session_id, {"jsonrpc": "2.0", "id": msg_id, "result": result})
                return JSONResponse({"ok": True}, status_code=202)

            if method in ("notifications/initialized",):
                return JSONResponse({"ok": True}, status_code=202)

            if method in ("list_tools", "tools/list"):
                # Plugin: before_cache_lookup
                plugin_cache = await plugin_manager.execute_first(
                    "on_before_cache_lookup", slug=slug,
                )
                if plugin_cache is not None:
                    _tools_cache[slug] = plugin_cache

                cached = _tools_cache.get(_cache_key(slug))
                if not _is_cache_expired(cached):
                    _cache_hits += 1
                    tools = cached[1]
                else:
                    _cache_misses += 1
                    async with _engine_locks[slug]:
                        cached = _tools_cache.get(_cache_key(slug))
                        if _is_cache_expired(cached):
                            _tools_cache[slug] = (
                                time.time(),
                                await engine.list_tools(slug),
                            )
                    tools = _tools_cache[slug][1]

                # Plugin: after_cache_lookup
                await plugin_manager.execute("on_after_cache_lookup", slug=slug, tools=tools)

                _send_to_session(
                    session_id,
                    {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}},
                )
                return JSONResponse({"ok": True}, status_code=202)

            if method in ("call_tool", "tools/call"):
                name = body.get("params", {}).get("name", "")
                arguments = body.get("params", {}).get("arguments", {})
                result = await engine.call_tool(slug, name, arguments)
                _send_to_session(
                    session_id,
                    {"jsonrpc": "2.0", "id": msg_id, "result": result},
                )
                return JSONResponse({"ok": True}, status_code=202)

            send_error(-32601, f"Method not found: {method}")
            return JSONResponse({"ok": True}, status_code=202)

        except PermissionError as e:
            send_error(-32001, str(e))
            return JSONResponse({"ok": True}, status_code=202)
        except ValueError as e:
            send_error(-32602, str(e))
            return JSONResponse({"ok": True}, status_code=202)
        except Exception as e:
            log.exception("Proxy error handling %s for %s", method, slug)
            send_error(-32603, str(e))
            return JSONResponse({"ok": True}, status_code=202)
