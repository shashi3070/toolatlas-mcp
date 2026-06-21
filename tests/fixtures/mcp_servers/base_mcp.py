import json
import logging
import uuid
import threading
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

log = logging.getLogger(__name__)


class ToolDef:
    def __init__(self, name: str, description: str, input_schema: dict[str, Any], mock_result: Any = None):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.mock_result = mock_result or {"content": [{"type": "text", "text": f"Result from {name}"}]}


class BaseMockMCPServer:
    def __init__(self, name: str, port: int, tools: list[ToolDef], latency: float = 0.0, error_rate: float = 0.0):
        self.name = name
        self.port = port
        self.tools = {t.name: t for t in tools}
        self.latency = latency
        self.error_rate = error_rate
        self.app = self._build_app()
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None

    def _build_app(self) -> FastAPI:
        app = FastAPI(title=f"Mock {self.name} MCP Server")

        sessions: dict[str, list] = {}

        @app.get("/sse")
        async def sse(request: Request):
            session_id = str(uuid.uuid4())
            sessions[session_id] = []

            async def event_gen():
                message_url = f"/message/{session_id}"
                yield {"event": "endpoint", "data": message_url}
                while True:
                    if await request.is_disconnected():
                        break
                    msgs = sessions.get(session_id, [])
                    while msgs:
                        msg = msgs.pop(0)
                        yield {"event": "message", "data": json.dumps(msg)}
                    import asyncio
                    await asyncio.sleep(0.05)

            return EventSourceResponse(event_gen())

        @app.post("/message/{session_id}")
        async def message(session_id: str, request: Request):
            body = await request.json()
            msg_id = body.get("id")
            method = body.get("method", "")
            params = body.get("params", {})

            import asyncio
            if self.latency > 0:
                await asyncio.sleep(self.latency)

            import random
            if self.error_rate > 0 and random.random() < self.error_rate:
                return JSONResponse({
                    "jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32000, "message": "Simulated error"},
                })

            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": self.name, "version": "1.0.0"},
                }
                sessions[session_id].append({"jsonrpc": "2.0", "id": msg_id, "result": result})
                return JSONResponse({"jsonrpc": "2.0", "id": msg_id, "result": result})

            elif method == "notifications/initialized":
                return JSONResponse({"jsonrpc": "2.0", "result": {}})

            elif method in ("list_tools", "tools/list"):
                tools_list = [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.input_schema,
                    }
                    for t in self.tools.values()
                ]
                result = {"tools": tools_list}
                sessions[session_id].append({"jsonrpc": "2.0", "id": msg_id, "result": result})
                return JSONResponse({"jsonrpc": "2.0", "id": msg_id, "result": result})

            elif method in ("call_tool", "tools/call"):
                name = params.get("name", "")
                tool = self.tools.get(name)
                if not tool:
                    return JSONResponse({
                        "jsonrpc": "2.0", "id": msg_id,
                        "error": {"code": -32602, "message": f"Tool '{name}' not found"},
                    })
                result = tool.mock_result
                sessions[session_id].append({"jsonrpc": "2.0", "id": msg_id, "result": result})
                return JSONResponse({"jsonrpc": "2.0", "id": msg_id, "result": result})

            else:
                return JSONResponse({
                    "jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                })

        return app

    def start(self):
        config = uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="error")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        import time
        time.sleep(0.5)

    def stop(self):
        if self._server:
            self._server.should_exit = True
            if self._thread:
                self._thread.join(timeout=5)
