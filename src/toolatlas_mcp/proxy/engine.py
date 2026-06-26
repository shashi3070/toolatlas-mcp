import asyncio
import logging
from typing import Any

from toolatlas_mcp.proxy.middleware import ProxyMiddleware
from toolatlas_mcp.registry.mcp_client import MCPClient
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
    def __init__(self, storage: StorageBackend):
        self.storage = storage
        self.middleware = ProxyMiddleware(storage)
        self._server_clients: dict[str, MCPClient] = {}
        self._tool_to_server: dict[str, str] = {}
        self._tool_info: dict[str, dict] = {}


    async def initialize_proxy(self, slug: str):
        proxy = await self.storage.get_proxy_by_slug(slug)
        if not proxy:
            raise ValueError(f"Proxy '{slug}' not found")
        servers = await self.storage.get_proxy_servers(proxy["id"])
        for server in servers:
            if server["id"] not in self._server_clients:
                await self._connect_server(server)

    async def _connect_server(self, server: dict):
        client = MCPClient(
            transport=server["transport"],
            command=server.get("command"),
            url=server.get("url"),
        )
        for attempt in range(3):
            try:
                await client.connect()
                await client.initialize()
                self._server_clients[server["id"]] = client
                log.info("Connected to MCP server: %s", server["name"])
                return
            except Exception as e:
                if attempt < 2:
                    wait = (attempt + 1) * 2
                    log.warning("Failed to connect to MCP server '%s' (attempt %d/3): %s — retrying in %ds", server["name"], attempt + 1, e, wait)
                    await asyncio.sleep(wait)
                else:
                    log.warning("Failed to connect to MCP server '%s' after 3 attempts: %s", server["name"], e)

    async def list_tools(self, slug: str) -> list[dict[str, Any]]:
        proxy = await self.storage.get_proxy_by_slug(slug)
        if not proxy:
            raise ValueError(f"Proxy '{slug}' not found")

        servers = await self.storage.get_proxy_servers(proxy["id"])

        if not self._server_clients:
            log.info("No server clients for %s — reinitializing", slug)
            await self.initialize_proxy(slug)

        tools_map: dict[str, dict[str, Any]] = {}
        old_tts = dict(self._tool_to_server)
        old_ti = dict(self._tool_info)
        self._tool_to_server.clear()
        self._tool_info.clear()

        try:
            for server in servers:
                client = self._server_clients.get(server["id"])
                if not client:
                    continue
                try:
                    remote_tools = await client.list_tools()
                except Exception as e:
                    log.warning("Failed to list tools from '%s': %s", server["name"], e)
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
                    )

                    if not db_tool.get("enabled", True):
                        continue

                    setting = await self.storage.get_tool_setting(proxy["id"], db_tool["id"])
                    if setting and not setting.get("enabled", True):
                        continue
                    if setting is None:
                        selection = await self.storage.get_proxy_server_selection(proxy["id"], server["id"])
                        if selection is not None and tool_name not in selection:
                            await self.storage.upsert_tool_setting(proxy["id"], db_tool["id"], enabled=False)
                            continue

                    display_name = setting.get("alias") if setting and setting.get("alias") else db_tool["name"]
                    display_desc = setting.get("custom_description") or db_tool.get("description") if setting else db_tool.get("description", "")

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
                            enrichment.append(f"Glossary: {gt.get('definition') or gt.get('term')}")
                    if enrichment:
                        display_desc = (display_desc + "\n" + "\n".join(enrichment)) if display_desc else "\n".join(enrichment)

                    tools_map[tool_name] = {
                        "name": display_name,
                        "description": display_desc,
                        "inputSchema": rt.get("inputSchema", {}),
                    }
        except Exception:
            self._tool_to_server.update(old_tts)
            self._tool_info.update(old_ti)
            raise

        return list(tools_map.values())

    async def call_tool(self, slug: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        proxy = await self.storage.get_proxy_by_slug(slug)
        if not proxy:
            raise ValueError(f"Proxy '{slug}' not found")

        servers = await self.storage.get_proxy_servers(proxy["id"])

        if not self._server_clients:
            log.info("No server clients for %s — reinitializing before tool call", slug)
            await self.initialize_proxy(slug)

        if not self._tool_to_server:
            log.info("Tool→server map empty for %s — rebuilding via list_tools", slug)
            await self.list_tools(slug)
        if not self._tool_to_server:
            raise RuntimeError(f"No tools available for proxy '{slug}' — upstream servers may be unreachable")

        server_id = self._tool_to_server.get(name)
        server = next((s for s in servers if s["id"] == server_id), None) if server_id else None
        if not server:
            raise ValueError(f"Tool '{name}' not found in proxy '{slug}'")

        client = self._server_clients.get(server["id"])
        if not client:
            raise ValueError(f"Server '{server['name']}' not connected for proxy '{slug}'")

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
            ctx["add_event"]("tool_resolution", f"Tool '{name}' resolved to server '{server['name']}'", {
                "server": server["name"], "tool_enabled": setting.get("enabled", True) if setting else True,
            })
            if setting and not setting.get("enabled", True):
                ctx["add_event"]("tool_disabled", f"Tool '{name}' is disabled in proxy '{slug}'", {
                    "tool": name, "proxy": slug,
                })
                raise PermissionError(f"Tool '{name}' is disabled in proxy '{slug}'")

            ctx["add_event"]("server_call_start", f"Forwarding to MCP server '{server['name']}'", {
                "server": server["name"], "transport": server.get("transport"),
            })
            try:
                result = await asyncio.wait_for(client.call_tool(name, arguments), timeout=30)
            except asyncio.TimeoutError:
                log.warning("Tool call '%s' on server '%s' timed out after 30s", name, server["name"])
                raise TimeoutError(f"Tool '{name}' call timed out after 30s")
            except Exception:
                log.warning("Tool call '%s' failed on server '%s', attempting reconnect", name, server["name"])
                client.close()
                self._server_clients.pop(server["id"], None)
                await self._connect_server(server)
                client = self._server_clients.get(server["id"])
                if client is None:
                    raise RuntimeError(f"Failed to reconnect to server '{server['name']}'")
                result = await asyncio.wait_for(client.call_tool(name, arguments), timeout=30)

            ctx["add_event"]("server_response", f"Response from server '{server['name']}'", {
                "result_summary": str(result)[:300],
            })
            ctx["add_event"]("response_returned", "Response forwarded to client", {
                "result_summary": str(result)[:300],
            })
        return result

    def close(self):
        for client in self._server_clients.values():
            client.close()
        self._server_clients.clear()
        self._tool_to_server.clear()
        self._tool_info.clear()
