from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PluginContext:
    """Carries contextual information through the plugin hook chain."""

    slug: str = ""
    method: str = ""
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    server_id: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class Plugin:
    """Base class for all ToolAtlas plugins.

    Subclass this and override any of the hook methods.  All hooks are
    optional — only implement what you need.
    """

    name: str = ""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def startup(self):
        """Called once when the plugin is loaded."""

    async def shutdown(self):
        """Called during app shutdown."""

    # ------------------------------------------------------------------
    # Tool listing hooks
    # ------------------------------------------------------------------

    async def on_before_list_tools(self, ctx: PluginContext) -> list[dict] | None:
        """Return a tool list to short-circuit the normal flow, or None."""

    async def on_after_list_tools(self, ctx: PluginContext, tools: list[dict]) -> None:
        """Post-process the enriched tool list."""

    # ------------------------------------------------------------------
    # Tool call hooks
    # ------------------------------------------------------------------

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        """Validate / transform before forwarding.  Raise to block the call."""

    async def on_after_tool_call(self, ctx: PluginContext, result: dict) -> None:
        """Post-process the call response."""

    # ------------------------------------------------------------------
    # Server lifecycle hooks
    # ------------------------------------------------------------------

    async def on_server_connected(self, server_id: str) -> None:
        """Called when a shared connection to a server is established."""

    async def on_server_disconnected(self, server_id: str) -> None:
        """Called when a server connection is closed or lost."""

    # ------------------------------------------------------------------
    # Tool registry hooks
    # ------------------------------------------------------------------

    async def on_tool_added(self, server_id: str, tool_names: list[str]) -> None:
        """Called by the background registry sync when new tools appear."""

    async def on_tool_updated(self, server_id: str, tool_names: list[str]) -> None:
        """Called when tool definitions change."""

    async def on_tool_removed(self, server_id: str, tool_names: list[str]) -> None:
        """Called when tools disappear from the server."""

    # ------------------------------------------------------------------
    # Cache hooks
    # ------------------------------------------------------------------

    async def on_before_cache_lookup(self, slug: str) -> tuple[float, list] | None:
        """Return a cached (timestamp, tools) pair to short-circuit lookup."""

    async def on_after_cache_lookup(self, slug: str, tools: list) -> None:
        """Called after a cache hit/miss is resolved."""

    async def on_cache_invalidated(self, slug: str) -> None:
        """Called when a proxy's tool cache is invalidated."""
