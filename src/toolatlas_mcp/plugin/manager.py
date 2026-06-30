from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

from toolatlas_mcp.plugin.base import Plugin, PluginAbortError, PluginContext

log = logging.getLogger(__name__)


class PluginManager:
    """Discovers, loads, and executes plugin hooks."""

    def __init__(self):
        self._plugins: list[Plugin] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    @property
    def plugins(self) -> list[Plugin]:
        return list(self._plugins)

    def _sorted(self) -> list[Plugin]:
        return sorted(self._plugins, key=lambda p: p.priority)

    async def register(self, plugin: Plugin):
        """Register and start a single plugin instance."""
        await plugin.startup()
        self._plugins.append(plugin)
        self._plugins.sort(key=lambda p: p.priority)
        log.info("Plugin registered: %s (priority=%d)", plugin.name or type(plugin).__name__, plugin.priority)

    async def load_from_entry_point(self, dotted_path: str):
        """Import and register a plugin by dotted module path.

        The module must have a top-level ``plugin`` attribute that is
        a ``Plugin`` instance, or a ``Plugin`` subclass whose ``name``
        field matches the last component.
        """
        try:
            module = importlib.import_module(dotted_path)
            candidate = getattr(module, "plugin", None)
            if candidate is None:
                # Try the last segment of the dotted path as a class name
                parts = dotted_path.split(".")
                cls_name = parts[-1]
                cls = getattr(module, cls_name, None)
                if cls is not None and issubclass(cls, Plugin):
                    candidate = cls()
            if isinstance(candidate, Plugin):
                await self.register(candidate)
            else:
                log.warning("Entry point %s does not expose a Plugin instance", dotted_path)
        except Exception as e:
            log.error("Failed to load plugin from %s: %s", dotted_path, e)

    async def discover(self, plugin_dirs: list[Path]):
        """Scan directories for ``plugin.py`` files and import them."""
        for d in plugin_dirs:
            if not d.is_dir():
                continue
            for subdir in d.iterdir():
                plugin_file = subdir / "plugin.py"
                if plugin_file.exists():
                    dotted = str(plugin_file.with_suffix("")).replace(str(d.parent), "").strip("/\\").replace("/", ".").replace("\\", ".")
                    await self.load_from_entry_point(dotted)

    # ------------------------------------------------------------------
    # Hook execution
    # ------------------------------------------------------------------

    async def execute(self, hook: str, **kwargs: Any) -> list[Any]:
        """Call *hook* on every registered plugin.  Returns list of results."""
        results: list[Any] = []
        for plugin in self._sorted():
            method = getattr(plugin, hook, None)
            if method is None:
                continue
            try:
                result = await method(**kwargs)
                results.append(result)
            except PluginAbortError:
                raise
            except Exception as e:
                log.error("Plugin %s hook %s error: %s", plugin.name or type(plugin).__name__, hook, e)
        return results

    async def execute_first(self, hook: str, **kwargs: Any) -> Any | None:
        """Call *hook* until the first non-None result is returned."""
        for plugin in self._sorted():
            method = getattr(plugin, hook, None)
            if method is None:
                continue
            try:
                result = await method(**kwargs)
                if result is not None:
                    return result
            except PluginAbortError:
                raise
            except Exception as e:
                log.error("Plugin %s hook %s error: %s", plugin.name or type(plugin).__name__, hook, e)
        return None

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def shutdown_all(self):
        for plugin in self._plugins:
            try:
                await plugin.shutdown()
            except Exception as e:
                log.error("Plugin %s shutdown error: %s", plugin.name or type(plugin).__name__, e)
        self._plugins.clear()

    async def clear(self):
        """Remove all plugins without shutdown (for test isolation)."""
        self._plugins.clear()


plugin_manager = PluginManager()
