import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from toolatlas_mcp.plugin.manager import plugin_manager
from toolatlas_mcp.registry.storage import StorageBackend
from toolatlas_mcp.services.connection_manager import ConnectionManager

log = logging.getLogger(__name__)

_SYNC_INTERVAL = 30  # seconds, configurable via settings


def _compute_tool_hash(remote_tools: list[dict]) -> str:
    """SHA-256 of sorted tool definitions, used to detect changes."""
    sorted_tools = sorted(remote_tools, key=lambda t: t.get("name", ""))
    raw = json.dumps(sorted_tools, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


class RegistrySyncService:
    """Periodically syncs tool metadata from all upstream MCP servers.

    Runs every *_SYNC_INTERVAL* seconds.  For each enabled server it
    fetches the current tool list via the shared *ConnectionManager*,
    compares the SHA-256 hash against the stored value, and updates the
    database + invalidates affected proxy caches only when changes are
    detected.
    """

    def __init__(self):
        self._task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self, storage: StorageBackend, cm: ConnectionManager):
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._sync_loop(storage, cm))
        log.info("RegistrySyncService started (interval=%ss)", _SYNC_INTERVAL)

    async def stop(self):
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
            log.info("RegistrySyncService stopped")

    # ------------------------------------------------------------------
    # Sync loop
    # ------------------------------------------------------------------

    async def _sync_loop(self, storage: StorageBackend, cm: ConnectionManager):
        while True:
            try:
                servers = await storage.list_servers()
                for server in servers:
                    if not server.get("enabled", True):
                        continue
                    await self._sync_server(storage, cm, server)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("Registry sync error: %s", e)
            await asyncio.sleep(_SYNC_INTERVAL)

    async def _sync_server(
        self, storage: StorageBackend, cm: ConnectionManager, server: dict,
    ) -> dict[str, list[str]]:
        """Sync a single server.  Returns {added, updated, removed, unchanged}."""
        result: dict[str, list[str]] = {
            "added": [], "updated": [], "removed": [], "unchanged": [],
        }

        try:
            client = await cm.get_client(server)
        except Exception as e:
            log.warning("Registry sync: cannot connect to '%s': %s", server.get("name"), e)
            return result

        try:
            remote_tools = await client.list_tools()
        except Exception as e:
            log.warning("Registry sync: list_tools failed for '%s': %s", server.get("name"), e)
            return result

        new_hash = _compute_tool_hash(remote_tools)
        current_hash = server.get("tool_hash") or ""

        if new_hash == current_hash:
            result["unchanged"] = [t["name"] for t in remote_tools]
            return result

        # Build a name→id map of existing tools
        existing_tools = await storage.list_tools(server_id=server["id"])
        existing_by_name: dict[str, Any] = {t["name"]: t for t in existing_tools}
        remote_names = {t["name"] for t in remote_tools}

        db_tools = await storage.upsert_tools(
            server_id=server["id"],
            tools=[
                {"name": rt.get("name", ""), "description": rt.get("description", ""),
                 "input_schema": rt.get("inputSchema", {})}
                for rt in remote_tools
            ],
            auto_commit=False,
        )
        for dt, rt in zip(db_tools, remote_tools):
            name = rt["name"]
            if name not in existing_by_name:
                result["added"].append(name)
            else:
                result["updated"].append(name)

        # Removed tools
        removed_names = [name for name in existing_by_name if name not in remote_names]
        removed_ids = [existing_by_name[name]["id"] for name in removed_names]
        if removed_ids:
            await storage.delete_tools(removed_ids, auto_commit=False)
            result["removed"] = removed_names

        await storage.commit()

        now = datetime.now(timezone.utc)
        await storage.update_server(
            server["id"],
            tool_hash=new_hash,
            last_tool_sync=now,
            connection_status="connected",
        )

        # Invalidate proxy caches that reference this server
        from toolatlas_mcp.proxy.server import invalidate_proxies_for_server
        await invalidate_proxies_for_server(server["id"], storage)

        total_changed = len(result["added"]) + len(result["updated"]) + len(result["removed"])
        if total_changed:
            log.info(
                "Registry sync '%s': +%d -%d ~%d tools (hash %s…)",
                server.get("name"),
                len(result["added"]),
                len(result["removed"]),
                len(result["updated"]),
                new_hash[:8],
            )
        else:
            log.debug("Registry sync '%s': hash changed but no tool diff", server.get("name"))

        # Plugin hooks
        sid = server["id"]
        if result["added"]:
            await plugin_manager.execute("on_tool_added", server_id=sid, tool_names=result["added"])
        if result["updated"]:
            await plugin_manager.execute("on_tool_updated", server_id=sid, tool_names=result["updated"])
        if result["removed"]:
            await plugin_manager.execute("on_tool_removed", server_id=sid, tool_names=result["removed"])

        return result
