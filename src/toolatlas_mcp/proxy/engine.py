import asyncio
import logging
import time
from typing import Any

from toolatlas_mcp.plugin.base import PluginContext
from toolatlas_mcp.plugin.manager import plugin_manager
from toolatlas_mcp.proxy.middleware import ProxyMiddleware
from toolatlas_mcp.services.connection_manager import connection_manager
from toolatlas_mcp.registry.storage import StorageBackend

log = logging.getLogger(__name__)


def close_all_engines():
    from toolatlas_mcp.proxy.server import _engines as engine_dict, _engine_locks
    for slug, eng in list(engine_dict.items()):
        try:
            eng.close()
        except Exception as e:
            log.warning("Error closing engine for %s: %s", slug, e)
    engine_dict.clear()
    _engine_locks.clear()


class ProxyEngine:
    """Per-proxy-slot engine that resolves tools and forwards calls.

    Connections to upstream MCP servers are managed by the shared
    *connection_manager* — this class only maintains the tool-name →
    server-id mapping and enrichment logic.
    """

    def __init__(self, storage: StorageBackend):
        self.storage = storage
        self.middleware = ProxyMiddleware(storage)
        self._tool_to_server: dict[str, str] = {}
        self._tool_info: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    async def initialize_proxy(self, slug: str):
        proxy = await self.storage.get_proxy_by_slug(slug)
        if not proxy:
            raise ValueError(f"Proxy '{slug}' not found")
        servers = await self.storage.get_proxy_servers(proxy["id"])
        for server in servers:
            try:
                await connection_manager.get_client(server)
            except Exception as e:
                log.warning("Failed to connect to '%s' during init: %s", server.get("name"), e)

    # ------------------------------------------------------------------
    # list_tools
    # ------------------------------------------------------------------

    async def list_tools(self, slug: str) -> list[dict[str, Any]]:
        proxy = await self.storage.get_proxy_by_slug(slug)
        if not proxy:
            raise ValueError(f"Proxy '{slug}' not found")

        servers = await self.storage.get_proxy_servers(proxy["id"])

        tools_map: dict[str, dict[str, Any]] = {}
        old_tts = dict(self._tool_to_server)
        old_ti = dict(self._tool_info)
        self._tool_to_server.clear()
        self._tool_info.clear()

        try:
            for server in servers:
                try:
                    client = await connection_manager.get_client(server)
                except Exception:
                    log.warning("Skipping server '%s' (unreachable)", server.get("name"))
                    continue

                try:
                    remote_tools = await client.list_tools()
                except Exception as e:
                    log.warning(
                        "Failed to list tools from '%s': %s — reconnecting",
                        server["name"], e,
                    )
                    await connection_manager.remove_client(server["id"])
                    try:
                        client = await connection_manager.get_client(server)
                        remote_tools = await client.list_tools()
                    except Exception as e2:
                        log.warning(
                            "Failed to list tools from '%s' after reconnect: %s",
                            server["name"], e2,
                        )
                        continue

                for rt in remote_tools:
                    tool_name = rt.get("name", "")
                    self._tool_to_server[tool_name] = server["id"]
                    self._tool_info[tool_name] = rt

                    db_tool = await self.storage.upsert_tool(
                        server_id=server["id"],
                        name=tool_name,
                        description=rt.get("description", ""),
                        input_schema=rt.get("inputSchema", {}),
                        auto_commit=False,
                    )

                    if not db_tool.get("enabled", True):
                        continue

                    setting = await self.storage.get_tool_setting(proxy["id"], db_tool["id"])
                    if setting and not setting.get("enabled", True):
                        continue
                    if setting is None:
                        selection = await self.storage.get_proxy_server_selection(
                            proxy["id"], server["id"]
                        )
                        if selection is not None and tool_name not in selection:
                            await self.storage.upsert_tool_setting(
                                proxy["id"], db_tool["id"], enabled=False, auto_commit=False,
                            )
                            continue

                    display_name = (
                        setting.get("alias") if setting and setting.get("alias") else db_tool["name"]
                    )
                    display_desc = (
                        setting.get("custom_description") or db_tool.get("description")
                        if setting else db_tool.get("description", "")
                    )

                    enrichment = []
                    tags = db_tool.get("tags", [])
                    if tags:
                        enrichment.append(f"Tags: {', '.join(tags)}")
                    raw_domains = db_tool.get("domain", [])
                    if isinstance(raw_domains, str):
                        raw_domains = [raw_domains]
                    if raw_domains:
                        enrichment.append(f"Domain: {', '.join(raw_domains)}")
                    gt_ids = db_tool.get("glossary_term_ids", [])
                    if isinstance(gt_ids, str):
                        gt_ids = [gt_ids]
                    for gid in gt_ids:
                        gt = await self.storage.get_glossary_term(gid)
                        if gt:
                            enrichment.append(
                                f"Glossary: {gt.get('definition') or gt.get('term')}"
                            )
                    if enrichment:
                        display_desc = (
                            (display_desc + "\n" + "\n".join(enrichment))
                            if display_desc else "\n".join(enrichment)
                        )

                    tools_map[tool_name] = {
                        "name": display_name,
                        "description": display_desc,
                        "inputSchema": rt.get("inputSchema", {}),
                    }
                await self.storage.commit()
        except Exception:
            self._tool_to_server.update(old_tts)
            self._tool_info.update(old_ti)
            raise

        tools = list(tools_map.values())

        # Plugin: after_list_tools
        ctx = PluginContext(slug=slug, method="list_tools")
        await plugin_manager.execute("on_after_list_tools", ctx=ctx, tools=tools)

        return tools

    # ------------------------------------------------------------------
    # call_tool
    # ------------------------------------------------------------------

    async def call_tool(
        self, slug: str, name: str, arguments: dict[str, Any],
    ) -> dict[str, Any]:
        proxy = await self.storage.get_proxy_by_slug(slug)
        if not proxy:
            raise ValueError(f"Proxy '{slug}' not found")

        servers = await self.storage.get_proxy_servers(proxy["id"])

        if not self._tool_to_server:
            log.info("Tool→server map empty for %s — rebuilding via list_tools", slug)
            await self.list_tools(slug)
        if not self._tool_to_server:
            raise RuntimeError(
                f"No tools available for proxy '{slug}' — upstream servers may be unreachable"
            )

        server_id = self._tool_to_server.get(name)
        server = (
            next((s for s in servers if s["id"] == server_id), None) if server_id else None
        )
        if not server:
            raise ValueError(f"Tool '{name}' not found in proxy '{slug}'")

        try:
            client = await connection_manager.get_client(server)
        except Exception as e:
            raise RuntimeError(
                f"Server '{server['name']}' unreachable for proxy '{slug}': {e}"
            )

        remote_tool = self._tool_info.get(name, {})
        db_tool = await self.storage.upsert_tool(
            server_id=server["id"],
            name=name,
            description=remote_tool.get("description", ""),
            input_schema=remote_tool.get("inputSchema", {}),
        )

        setting = await self.storage.get_tool_setting(proxy["id"], db_tool["id"])

        async with self.middleware.track(
            tool_name=name,
            proxy_id=proxy["id"],
            tool_id=db_tool["id"],
            server_id=server["id"],
            request_args=arguments,
        ) as ctx:
            ctx["add_event"]("proxy_lookup", f"Proxy '{slug}' resolved", {
                "proxy_slug": slug, "proxy_name": proxy["name"],
            })
            ctx["add_event"]("tool_resolution",
                             f"Tool '{name}' resolved to server '{server['name']}'", {
                "server": server["name"],
                "tool_enabled": setting.get("enabled", True) if setting else True,
            })
            if setting and not setting.get("enabled", True):
                ctx["add_event"]("tool_disabled",
                                 f"Tool '{name}' is disabled in proxy '{slug}'", {
                    "tool": name, "proxy": slug,
                })
                raise PermissionError(f"Tool '{name}' is disabled in proxy '{slug}'")

            # Plugin: before_tool_call
            pctx = PluginContext(
                slug=slug, method="call_tool",
                tool_name=name, arguments=arguments,
                server_id=server["id"],
            )
            await plugin_manager.execute("on_before_tool_call", ctx=pctx)

            ctx["add_event"]("server_call_start",
                             f"Forwarding to MCP server '{server['name']}'", {
                "server": server["name"], "transport": server.get("transport"),
            })
            try:
                result = await asyncio.wait_for(
                    client.call_tool(name, arguments), timeout=30,
                )
            except asyncio.TimeoutError:
                log.warning(
                    "Tool call '%s' on server '%s' timed out after 30s",
                    name, server["name"],
                )
                raise TimeoutError(f"Tool '{name}' call timed out after 30s")
            except Exception:
                log.warning(
                    "Tool call '%s' failed on server '%s', attempting reconnect",
                    name, server["name"],
                )
                await connection_manager.remove_client(server["id"])
                try:
                    client = await connection_manager.get_client(server)
                    result = await asyncio.wait_for(
                        client.call_tool(name, arguments), timeout=30,
                    )
                except Exception as e2:
                    raise RuntimeError(
                        f"Failed to reconnect to server '{server['name']}': {e2}"
                    )

            ctx["add_event"]("server_response", f"Response from server '{server['name']}'", {
                "result_summary": str(result)[:300],
            })
            ctx["add_event"]("response_returned", "Response forwarded to client", {
                "result_summary": str(result)[:300],
            })

        # Plugin: after_tool_call
        pctx.extra["duration_ms"] = (time.time() - pctx.extra.get("start_time", time.time())) * 1000
        await plugin_manager.execute("on_after_tool_call", ctx=pctx, result=result)

        return result

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        self._tool_to_server.clear()
        self._tool_info.clear()
