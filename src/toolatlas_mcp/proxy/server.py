import json
import logging
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from toolatlas_mcp.db import async_session_factory
from toolatlas_mcp.proxy.engine import ProxyEngine

log = logging.getLogger(__name__)

router = APIRouter()

_sessions: dict[str, dict] = {}


async def get_engine() -> ProxyEngine:
    db = async_session_factory()
    return ProxyEngine(db)


@router.get("/proxy/{slug}/sse")
async def proxy_sse(slug: str, request: Request):
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"slug": slug}

    async def event_generator():
        message_url = f"/proxy/{slug}/message/{session_id}"
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

    engine = await get_engine()
    try:
        await engine.initialize_proxy(slug)

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "toolatlas-mcp", "version": "0.1.0"},
            }
            _sessions[session_id] = {"initialized": True}
            return JSONResponse({"jsonrpc": "2.0", "id": msg_id, "result": result})

        elif method == "notifications/initialized":
            return JSONResponse({"jsonrpc": "2.0", "id": msg_id, "result": {}})

        elif method == "list_tools":
            tools = await engine.list_tools(slug)
            return JSONResponse({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {"tools": tools},
            })

        elif method == "call_tool":
            name = body.get("params", {}).get("name", "")
            arguments = body.get("params", {}).get("arguments", {})
            result = await engine.call_tool(slug, name, arguments)
            return JSONResponse({
                "jsonrpc": "2.0", "id": msg_id,
                "result": result,
            })

        else:
            return JSONResponse({
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            })

    except ValueError as e:
        return JSONResponse({
            "jsonrpc": "2.0", "id": msg_id,
            "error": {"code": -32602, "message": str(e)},
        })
    except PermissionError as e:
        return JSONResponse({
            "jsonrpc": "2.0", "id": msg_id,
            "error": {"code": -32001, "message": str(e)},
        })
    except Exception as e:
        log.exception("Proxy error")
        return JSONResponse({
            "jsonrpc": "2.0", "id": msg_id,
            "error": {"code": -32603, "message": str(e)},
        })
