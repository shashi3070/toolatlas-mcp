import os
import sys
from pathlib import Path
from typing import Any


def get_data_dir() -> Path:
    env_dir = os.environ.get("TOOLATLAS_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "ToolAtlas"
    return Path.home() / ".toolatlas"


class StorageBackend:
    async def close(self):
        pass

    async def create_server(self, name: str, transport: str = "sse", command: str | None = None, url: str | None = None) -> Any:
        raise NotImplementedError

    async def list_servers(self) -> list[Any]:
        raise NotImplementedError

    async def get_server(self, server_id: str) -> Any | None:
        raise NotImplementedError

    async def update_server(self, server_id: str, **kwargs) -> Any | None:
        raise NotImplementedError

    async def delete_server(self, server_id: str) -> bool:
        raise NotImplementedError

    async def upsert_tool(self, server_id: str, name: str, description: str, input_schema: dict[str, Any]) -> Any:
        raise NotImplementedError

    async def list_tools(self, server_id: str | None = None) -> list[Any]:
        raise NotImplementedError

    async def get_tool(self, tool_id: str) -> Any | None:
        raise NotImplementedError

    async def update_tool(self, tool_id: str, **kwargs) -> Any | None:
        raise NotImplementedError

    async def delete_tool(self, tool_id: str) -> bool:
        raise NotImplementedError

    async def create_proxy(self, name: str, slug: str, description: str = "") -> Any:
        raise NotImplementedError

    async def list_proxies(self) -> list[Any]:
        raise NotImplementedError

    async def get_proxy(self, proxy_id: str) -> Any | None:
        raise NotImplementedError

    async def get_proxy_by_slug(self, slug: str) -> Any | None:
        raise NotImplementedError

    async def update_proxy(self, proxy_id: str, **kwargs) -> Any | None:
        raise NotImplementedError

    async def delete_proxy(self, proxy_id: str) -> bool:
        raise NotImplementedError

    async def link_server_to_proxy(self, proxy_id: str, server_id: str, selected_tools: list[str] | None = None):
        raise NotImplementedError

    async def get_proxy_server_selection(self, proxy_id: str, server_id: str) -> list[str] | None:
        raise NotImplementedError

    async def unlink_server_from_proxy(self, proxy_id: str, server_id: str):
        raise NotImplementedError

    async def get_proxy_servers(self, proxy_id: str) -> list[Any]:
        raise NotImplementedError

    async def get_tool_setting(self, proxy_id: str, tool_id: str) -> Any | None:
        raise NotImplementedError

    async def upsert_tool_setting(self, proxy_id: str, tool_id: str, enabled: bool | None = None, custom_description: str | None = None, alias: str | None = None) -> Any:
        raise NotImplementedError

    async def create_glossary_term(self, term: str, definition: str = "") -> Any:
        raise NotImplementedError

    async def list_glossary_terms(self) -> list[Any]:
        raise NotImplementedError

    async def get_glossary_term(self, term_id: str) -> Any | None:
        raise NotImplementedError

    async def update_glossary_term(self, term_id: str, **kwargs) -> Any | None:
        raise NotImplementedError

    async def delete_glossary_term(self, term_id: str) -> bool:
        raise NotImplementedError

    async def create_domain(self, name: str, description: str = "") -> Any:
        raise NotImplementedError

    async def list_domains(self) -> list[Any]:
        raise NotImplementedError

    async def record_call(
        self,
        tool_name: str,
        proxy_id: str | None = None,
        tool_id: str | None = None,
        server_id: str | None = None,
        request_args: dict | None = None,
        response_summary: str | None = None,
        duration_ms: float = 0.0,
        success: bool = True,
        error_message: str | None = None,
        client_id: str | None = None,
        trace_id: str | None = None,
        events: list | None = None,
    ) -> Any:
        raise NotImplementedError

    async def get_call(self, call_id: str) -> Any | None:
        raise NotImplementedError

    async def list_calls(self, proxy_id: str | None = None, tool_id: str | None = None, limit: int = 100, offset: int = 0) -> list[Any]:
        raise NotImplementedError

    async def get_call_stats(self) -> dict[str, Any]:
        raise NotImplementedError

    async def get_proxy_stats(self, proxy_id: str) -> dict[str, Any]:
        raise NotImplementedError
