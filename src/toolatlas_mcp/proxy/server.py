import asyncio
import json
import logging
import time
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from toolatlas_mcp import __version__
from toolatlas_mcp.db import get_storage
from toolatlas_mcp.proxy.engine import ProxyEngine

log = logging.getLogger(__name__)

router = APIRouter()

_session_queues: dict[str, asyncio.Queue] = {}
_engines: dict[str, ProxyEngine] = {}
_engine_locks: dict[str, asyncio.Lock] = {}
_TOOLS_CACHE_TTL = 60
_tools_cache: dict[str, tuple[float, list]] = {}


def _send_to_session(session_id: str, response: dict):
    q = _session_queues.get(session_id)
    if q is None:
        return
    try:
        q.put_nowait(response)
    except asyncio.QueueFull:
        log.warning("Session %s queue full, dropping response", session_id)


def invalidate_proxy_cache(slug: str):
    _tools_cache.pop(slug, None)
    if slug in _engines:
        _engines[slug].close()
        del _engines[slug]
        _engine_locks.pop(slug, None)


async def _get_engine(slug: str, storage) -> ProxyEngine:
    if slug not in _engine_locks:
        _engine_locks[slug] = asyncio.Lock()
    async with _engine_locks[slug]:
        if slug in _engines:
            if not _engines[slug]._server_clients:
                log.info("Reinitializing proxy engine for %s (no server clients)", slug)
                _tools_cache.pop(slug, None)
                await _engines[slug].initialize_proxy(slug)
            _engines[slug].storage = storage
            _engines[slug].middleware.storage = storage
            return _engines[slug]
        engine = ProxyEngine(storage)
        await engine.initialize_proxy(slug)
        _engines[slug] = engine
        return engine


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
    try:
        body = await request.json()
    except Exception as e:
        log.exception("Failed to parse request body")
        return JSONResponse({"ok": True}, status_code=202)

    method = body.get("method", "")
    msg_id = body.get("id")

    def send_error(code: int, message: str):
        if msg_id is not None:
            _send_to_session(session_id, {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}})

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
                cached = _tools_cache.get(slug)
                if cached is None or time.time() - cached[0] > _TOOLS_CACHE_TTL:
                    _tools_cache[slug] = (time.time(), await engine.list_tools(slug))
                tools = _tools_cache[slug][1]
                _send_to_session(session_id, {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}})
                return JSONResponse({"ok": True}, status_code=202)

            if method in ("call_tool", "tools/call"):
                name = body.get("params", {}).get("name", "")
                arguments = body.get("params", {}).get("arguments", {})
                result = await engine.call_tool(slug, name, arguments)
                _send_to_session(session_id, {"jsonrpc": "2.0", "id": msg_id, "result": result})
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
