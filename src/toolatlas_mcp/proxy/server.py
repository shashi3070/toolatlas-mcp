import json
import logging
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from toolatlas_mcp import __version__
from toolatlas_mcp.db import get_storage
from toolatlas_mcp.proxy.engine import ProxyEngine

log = logging.getLogger(__name__)

router = APIRouter()

_sessions: dict[str, dict] = {}


def _make_response(msg_id: str | int | None, result: dict | None = None, error: dict | None = None) -> JSONResponse:
    body: dict = {"jsonrpc": "2.0"}
    if msg_id is not None:
        body["id"] = msg_id
    if error:
        body["error"] = error
    else:
        body["result"] = result or {}
    return JSONResponse(body)


def _send_to_session(session_id: str, response: dict):
    if session_id in _sessions:
        _sessions[session_id]["response"] = response


@router.get("/proxy/{slug}/sse")
async def proxy_sse(slug: str, request: Request):
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"slug": slug}

    async def event_generator():
        base = request.app.root_path or ""
        message_url = f"{base}/proxy/{slug}/message/{session_id}"
        yield {"event": "endpoint", "data": message_url}

        try:
            while True:
                if await request.is_disconnected():
                    break
                session = _sessions.get(session_id)
                if session and "response" in session:
                    response = session.pop("response")
                    yield {"event": "message", "data": json.dumps(response)}
                import asyncio
                await asyncio.sleep(0.1)
        finally:
            _sessions.pop(session_id, None)

    return EventSourceResponse(event_generator())


@router.post("/proxy/{slug}/message/{session_id}")
async def proxy_message(slug: str, session_id: str, request: Request):
    body = await request.json()
    method = body.get("method", "")
    msg_id = body.get("id")

    async for storage in get_storage():
        engine = ProxyEngine(storage)
        try:
            await engine.initialize_proxy(slug)

            if method in ("initialize",):
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "toolatlas-mcp", "version": __version__},
                }
                _sessions[session_id] = {"initialized": True}
                return _make_response(msg_id, result)

            if method in ("notifications/initialized",):
                return _make_response(None, {})

            if method in ("list_tools", "tools/list"):
                tools = await engine.list_tools(slug)
                return _make_response(msg_id, {"tools": tools})

            if method in ("call_tool", "tools/call"):
                name = body.get("params", {}).get("name", "")
                arguments = body.get("params", {}).get("arguments", {})
                result = await engine.call_tool(slug, name, arguments)
                return _make_response(msg_id, result)

            return _make_response(msg_id, error={"code": -32601, "message": f"Method not found: {method}"})

        except ValueError as e:
            return _make_response(msg_id, error={"code": -32602, "message": str(e)})
        except PermissionError as e:
            return _make_response(msg_id, error={"code": -32001, "message": str(e)})
        except Exception as e:
            log.exception("Proxy error")
            return _make_response(msg_id, error={"code": -32603, "message": str(e)})
        finally:
            engine.close()
        break
