import logging
from typing import Any

from toolatlas_mcp.proxy.middleware import ProxyMiddleware
from toolatlas_mcp.registry.mcp_client import MCPClient
from toolatlas_mcp.registry.storage import StorageBackend

log = logging.getLogger(__name__)

_engines: list["ProxyEngine"] = []


def close_all_engines():
    for eng in list(_engines):
        try:
            eng.close()
        except Exception as e:
            log.warning("Error closing engine: %s", e)


class ProxyEngine:
    def __init__(self, storage: StorageBackend):
        self.storage = storage
        self.middleware = ProxyMiddleware(storage)
        self._server_clients: dict[str, MCPClient] = {}
        _engines.append(self)

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
        try:
            await client.connect()
            await client.initialize()
            self._server_clients[server["id"]] = client
            log.info("Connected to MCP server: %s", server["name"])
        except Exception as e:
            log.warning("Failed to connect to MCP server '%s': %s", server["name"], e)

    async def list_tools(self, slug: str) -> list[dict[str, Any]]:
        proxy = await self.storage.get_proxy_by_slug(slug)
        if not proxy:
            raise ValueError(f"Proxy '{slug}' not found")

        servers = await self.storage.get_proxy_servers(proxy["id"])
        tools_map: dict[str, dict[str, Any]] = {}

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

        return list(tools_map.values())

    async def call_tool(self, slug: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        proxy = await self.storage.get_proxy_by_slug(slug)
        if not proxy:
            raise ValueError(f"Proxy '{slug}' not found")

        servers = await self.storage.get_proxy_servers(proxy["id"])

        for server in servers:
            client = self._server_clients.get(server["id"])
            if not client:
                continue

            try:
                remote_tools = await client.list_tools()
            except Exception:
                continue

            remote_tool_match = next((rt for rt in remote_tools if rt.get("name") == name), None)
            if remote_tool_match:
                db_tool = await self.storage.upsert_tool(
                    server_id=server["id"],
                    name=name,
                    description=remote_tool_match.get("description", ""),
                    input_schema=remote_tool_match.get("inputSchema", {}),
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
                    result = await client.call_tool(name, arguments)
                    ctx["add_event"]("server_response", f"Response from server '{server['name']}'", {
                        "result_summary": str(result)[:300],
                    })
                    ctx["add_event"]("response_returned", "Response forwarded to client", {
                        "result_summary": str(result)[:300],
                    })
                return result

        raise ValueError(f"Tool '{name}' not found in proxy '{slug}'")

    def close(self):
        for client in self._server_clients.values():
            client.close()
        self._server_clients.clear()
        if self in _engines:
            _engines.remove(self)
