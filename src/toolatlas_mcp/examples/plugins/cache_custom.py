# Custom Cache Plugin

Demonstrates a custom in-memory cache using `on_before_list_tools` (short-circuit)
and `on_after_list_tools` (cache write).

## Running

```bash
python examples/plugins/cache_custom.py
```

## What It Demonstrates

- `on_before_list_tools` returning cached data to short-circuit the normal flow
- `on_after_list_tools` populating the cache
- TTL-based cache expiry
"""

import logging
import time

from toolatlas_mcp.plugin import Plugin, PluginContext, plugin_manager

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


class CustomCachePlugin(Plugin):
    name = "custom_cache"

    def __init__(self, ttl_sec: float = 30.0):
        self._cache: dict[str, tuple[float, list[dict]]] = {}
        self._ttl = ttl_sec
        self._hits = 0
        self._misses = 0

    async def on_before_list_tools(self, ctx: PluginContext) -> list[dict] | None:
        cached = self._cache.get(ctx.slug)
        if cached is not None:
            timestamp, tools = cached
            if time.time() - timestamp < self._ttl:
                self._hits += 1
                log.info("Cache HIT for %s (hits=%d, misses=%d)", ctx.slug, self._hits, self._misses)
                return tools  # short-circuit: return cached data
        self._misses += 1
        log.info("Cache MISS for %s (hits=%d, misses=%d)", ctx.slug, self._hits, self._misses)
        return None  # continue with normal flow

    async def on_after_list_tools(self, ctx: PluginContext, tools: list[dict]) -> None:
        self._cache[ctx.slug] = (time.time(), list(tools))
        log.info("Cached %d tools for %s", len(tools), ctx.slug)

    async def on_cache_invalidated(self, slug: str) -> None:
        self._cache.pop(slug, None)
        log.info("Invalidated cache for %s", slug)

    def stats(self) -> dict:
        return {"hits": self._hits, "misses": self._misses, "size": len(self._cache)}


plugin = CustomCachePlugin(ttl_sec=30.0)


async def main():
    await plugin_manager.register(plugin)
    log.info("Custom cache plugin registered")

    ctx = PluginContext(slug="dev", method="list_tools")

    # First call: miss
    tools = await plugin_manager.execute_first("on_before_list_tools", ctx=ctx)
    log.info("Before cache (1): %s", "MISS" if tools is None else f"HIT ({len(tools)} tools)")

    # After list_tools: plugins cache the result
    mock_tools = [{"name": "search_issues", "description": "Search Jira"}]
    await plugin_manager.execute("on_after_list_tools", ctx=ctx, tools=mock_tools)

    # Second call: hit
    tools = await plugin_manager.execute_first("on_before_list_tools", ctx=ctx)
    log.info("Before cache (2): %s", "MISS" if tools is None else f"HIT ({len(tools)} tools)")

    # Invalidate
    await plugin_manager.execute("on_cache_invalidated", slug=ctx.slug)

    # Third call: miss again
    tools = await plugin_manager.execute_first("on_before_list_tools", ctx=ctx)
    log.info("Before cache (3): %s", "MISS" if tools is None else f"HIT ({len(tools)} tools)")

    log.info("Stats: %s", plugin.stats())
    log.info("Example completed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
