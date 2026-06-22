import asyncio
import json
import logging
import uuid
from typing import Any

import httpx

log = logging.getLogger(__name__)


class MCPClient:
    def __init__(self, transport: str = "sse", command: str | None = None, url: str | None = None):
        self.transport = transport
        self.command = command
        self.url = url
        self._http_client: httpx.AsyncClient | None = None
        self._process: asyncio.subprocess.Process | None = None
        self._message_url: str | None = None
        self._pending: dict[str, asyncio.Future] = {}
        self._listener_task: asyncio.Task | None = None
        self._endpoint_received: asyncio.Event | None = None
        self._connected = False
        self._session_id: str | None = None

    async def connect(self):
        if self.transport == "sse":
            await self._connect_sse()
        elif self.transport == "streamable-http":
            await self._connect_streamable_http()
        elif self.transport == "stdio":
            await self._connect_stdio()
        else:
            raise ValueError(f"Unknown transport: {self.transport}")

    async def _connect_sse(self):
        if not self.url:
            raise ValueError("url is required for sse transport")
        sse_url = self.url.rstrip("/")
        if not sse_url.endswith("/sse"):
            sse_url += "/sse"

        self._endpoint_received = asyncio.Event()
        self._http_client = httpx.AsyncClient(timeout=None)

        async def sse_reader():
            try:
                async with self._http_client.stream(
                    "GET", sse_url, headers={"Accept": "text/event-stream"}
                ) as stream:
                    current_event = ""
                    async for line in stream.aiter_lines():
                        if line.startswith("event: endpoint"):
                            current_event = "endpoint"
                            continue
                        if line.startswith("event: "):
                            current_event = line[7:].strip()
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if current_event == "endpoint" or not self._message_url:
                                base = str(stream.url)
                                base = base[: base.rfind("/sse")]
                                self._message_url = f"{base}{data_str}"
                                self._endpoint_received.set()
                                current_event = ""
                            elif current_event == "message":
                                data = json.loads(data_str)
                                msg_id = data.get("id")
                                if msg_id and msg_id in self._pending:
                                    self._pending.pop(msg_id).set_result(data)
                                current_event = ""
                            else:
                                try:
                                    data = json.loads(data_str)
                                    msg_id = data.get("id")
                                    if msg_id and msg_id in self._pending:
                                        self._pending.pop(msg_id).set_result(data)
                                except json.JSONDecodeError:
                                    pass
                                current_event = ""
            except Exception as e:
                log.debug("SSE reader stopped: %s", e)

        self._listener_task = asyncio.create_task(sse_reader())
        await asyncio.wait_for(self._endpoint_received.wait(), timeout=10)
        self._connected = True

    async def _connect_streamable_http(self):
        if not self.url:
            raise ValueError("url is required for streamable-http transport")
        self._message_url = self.url
        self._http_client = httpx.AsyncClient(timeout=None)

        async def sse_reader():
            try:
                async with self._http_client.stream(
                    "GET", self._message_url,
                    headers={"Accept": "text/event-stream"},
                ) as stream:
                    async for line in stream.aiter_lines():
                        if line.startswith("data: "):
                            raw = line[6:].strip()
                            if not raw:
                                continue
                            try:
                                data = json.loads(raw)
                                msg_id = data.get("id")
                                if msg_id and msg_id in self._pending:
                                    self._pending.pop(msg_id).set_result(data)
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                log.debug("Streamable HTTP SSE reader stopped: %s", e)

        self._listener_task = asyncio.create_task(sse_reader())
        self._connected = True

    async def _connect_stdio(self):
        if not self.command:
            raise ValueError("command is required for stdio transport")
        self._process = await asyncio.create_subprocess_shell(
            self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._listener_task = asyncio.create_task(self._stdio_listener())
        self._connected = True

    async def _stdio_listener(self):
        if not self._process or not self._process.stdout:
            return
        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    break
                data = json.loads(line.decode().strip())
                msg_id = data.get("id")
                if msg_id and msg_id in self._pending:
                    self._pending.pop(msg_id).set_result(data)
        except Exception as e:
            log.debug("STDIO listener stopped: %s", e)

    async def send_request(self, method: str, params: dict | None = None) -> dict[str, Any]:
        is_notification = method.startswith("notifications/")
        msg_id = str(uuid.uuid4())
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if not is_notification:
            payload["id"] = msg_id
        payload["params"] = params or {}

        if not is_notification:
            future: asyncio.Future = asyncio.get_event_loop().create_future()
            self._pending[msg_id] = future

        try:
            if self.transport == "sse":
                await self._send_http(payload)
            elif self.transport == "streamable-http":
                await self._send_streamable_http(payload)
            elif self.transport == "stdio":
                await self._send_stdio(payload)
        except Exception:
            if not is_notification:
                self._pending.pop(msg_id, None)
                future.cancel()
            raise

        if is_notification:
            return {}

        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._pending.pop(msg_id, None)
            raise TimeoutError(f"MCP method '{method}' timed out")

    async def _send_http(self, payload: dict):
        if not self._http_client or not self._message_url:
            raise RuntimeError("MCP client not connected")
        resp = await self._http_client.post(self._message_url, json=payload)
        resp.raise_for_status()

    async def _send_streamable_http(self, payload: dict):
        if not self._http_client or not self._message_url:
            raise RuntimeError("MCP client not connected")
        headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
        async with self._http_client.stream(
            "POST", self._message_url, json=payload, headers=headers,
        ) as stream:
            self._session_id = stream.headers.get("mcp-session-id")
            if stream.status_code == 202:
                return
            if stream.status_code != 200:
                body = await stream.aread()
                detail = body.decode("utf-8", errors="replace")[:500]
                raise RuntimeError(
                    f"MCP server returned HTTP {stream.status_code}: {detail}"
                )
            if not stream.headers.get("content-type", "").startswith("text/event-stream"):
                raw = await stream.aread()
                if raw.strip():
                    data = json.loads(raw)
                    msg_id = data.get("id")
                    if msg_id and msg_id in self._pending:
                        self._pending.pop(msg_id).set_result(data)
                return
            current_event = ""
            async for line in stream.aiter_lines():
                if line.startswith("event: "):
                    current_event = line[7:].strip()
                elif line.startswith("data: "):
                    raw = line[6:].strip()
                    if not raw:
                        continue
                    data = json.loads(raw)
                    msg_id = data.get("id")
                    if msg_id and msg_id in self._pending:
                        self._pending.pop(msg_id).set_result(data)
                    return

    async def _send_stdio(self, payload: dict):
        if not self._process or not self._process.stdin:
            raise RuntimeError("MCP client not connected")
        line = json.dumps(payload) + "\n"
        self._process.stdin.write(line.encode())
        await self._process.stdin.drain()

    async def list_tools(self) -> list[dict[str, Any]]:
        resp = await self.send_request("tools/list")
        if "result" in resp:
            return resp["result"].get("tools", [])
        raise RuntimeError(f"list_tools failed: {resp.get('error')}")

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        resp = await self.send_request("tools/call", {"name": name, "arguments": arguments})
        if "result" in resp:
            return resp["result"]
        raise RuntimeError(f"call_tool failed: {resp.get('error')}")

    async def initialize(self):
        resp = await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "toolatlas-mcp", "version": "0.1.0"},
        })
        if "result" not in resp:
            raise RuntimeError(f"initialize failed: {resp.get('error')}")
        await self.send_request("notifications/initialized")

    async def close(self):
        self._connected = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except (asyncio.CancelledError, Exception):
                pass
            self._listener_task = None
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        if self._process:
            self._process.kill()
            await self._process.wait()
            self._process = None
        for fut in self._pending.values():
            fut.cancel()
        self._pending.clear()
