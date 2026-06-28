import asyncio
import logging
from typing import Any

from toolatlas_mcp.plugin.manager import plugin_manager
from toolatlas_mcp.registry.mcp_client import MCPClient

log = logging.getLogger(__name__)


class ConnectionManager:
    """Manages one MCPClient per server, shared across all proxies.

    Instead of each ProxyEngine creating its own connections to every
    upstream server, all proxies share a single pool of clients keyed
    by server_id.  This eliminates duplicate TCP connections, heartbeats,
    and initializations.
    """

    def __init__(self):
        self._clients: dict[str, MCPClient] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_client(self, server: dict) -> MCPClient:
        """Return a connected MCPClient for *server*, creating one if needed.

        Safe against concurrent access (per-server lock).  If the existing
        client's reader is done (stale), a new connection is established
        transparently.
        """
        server_id = server["id"]
        async with self._lock(server_id):
            existing = self._clients.get(server_id)
            if existing is not None:
                if not self._is_stale(existing):
                    return existing
                log.info("Replacing stale MCPClient for server %s", server.get("name", server_id))
                await self._close_client(server_id)

            client = MCPClient(
                transport=server.get("transport", "sse"),
                command=server.get("command"),
                url=server.get("url"),
            )
            for attempt in range(3):
                try:
                    await client.connect()
                    await client.initialize()
                    self._clients[server_id] = client
                    log.info("Connected (shared) to MCP server: %s", server.get("name", server_id))
                    await plugin_manager.execute("on_server_connected", server_id=server_id)
                    return client
                except Exception as e:
                    if attempt < 2:
                        wait = (attempt + 1) * 2
                        log.warning(
                            "Shared connect attempt %d/3 for '%s' failed: %s — retry in %ds",
                            attempt + 1, server.get("name", server_id), e, wait,
                        )
                        await asyncio.sleep(wait)
                    else:
                        log.warning(
                            "Shared connect to '%s' failed after 3 attempts: %s",
                            server.get("name", server_id), e,
                        )
                        raise

    async def remove_client(self, server_id: str):
        """Close and remove a single client (e.g. on server deletion)."""
        async with self._lock(server_id):
            await self._close_client(server_id)

    async def close_all(self):
        """Shutdown every managed client.  Called on app shutdown."""
        for sid in list(self._clients):
            await self._close_client(sid)

    async def clear(self):
        """Remove all clients without closing (for test isolation)."""
        self._clients.clear()
        self._locks.clear()

    def get_active_servers(self) -> list[str]:
        """Return server_ids of currently connected clients."""
        return [sid for sid, c in self._clients.items() if not self._is_stale(c)]

    def is_client_stale(self, server_id: str) -> bool:
        client = self._clients.get(server_id)
        return client is None or self._is_stale(client)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    @staticmethod
    def _is_stale(client: MCPClient) -> bool:
        reader = getattr(client, "_listener_task", None)
        return reader is not None and reader.done()

    async def _close_client(self, server_id: str):
        client = self._clients.pop(server_id, None)
        if client is not None:
            try:
                client.close()
            except Exception as e:
                log.debug("Error closing MCPClient for %s: %s", server_id, e)
        self._locks.pop(server_id, None)
        asyncio.ensure_future(plugin_manager.execute("on_server_disconnected", server_id=server_id))


connection_manager = ConnectionManager()
