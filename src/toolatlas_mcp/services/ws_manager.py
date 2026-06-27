import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

log = logging.getLogger(__name__)


class WSManager:
    def __init__(self):
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        log.info("WS client connected (%d total)", len(self._clients))

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self._clients.discard(websocket)
        log.info("WS client disconnected (%d total)", len(self._clients))

    async def broadcast(self, event_type: str, data: dict[str, Any]):
        payload = json.dumps({"type": event_type, "data": data})
        async with self._lock:
            dead: list[WebSocket] = []
            for ws in self._clients:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._clients.discard(ws)

    @property
    def client_count(self) -> int:
        return len(self._clients)


ws_manager = WSManager()
