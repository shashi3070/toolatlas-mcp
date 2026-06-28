# Error Handling Plugin

Demonstrates that a broken plugin does not crash the application — error isolation.

## Running

```bash
python examples/plugins/error_handling.py
```

## What It Demonstrates

- Plugin that raises in `on_before_tool_call`
- Other plugins still receive the event
- The engine can still call the tool
"""

import logging

from toolatlas_mcp.plugin import Plugin, PluginContext, plugin_manager

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


class GoodPlugin(Plugin):
    name = "good"

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        log.info("GoodPlugin: processing %s/%s", ctx.slug, ctx.tool_name)
        ctx.extra["good_ran"] = True

    async def on_after_tool_call(self, ctx: PluginContext, result: dict) -> None:
        log.info("GoodPlugin: call completed, success=%s", not result.get("isError"))


class BadPlugin(Plugin):
    name = "bad"

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        log.info("BadPlugin: about to crash...")
        raise RuntimeError("I am broken!")

    async def on_after_tool_call(self, ctx: PluginContext, result: dict) -> None:
        log.info("BadPlugin: this should still be reached (after crash is isolated)")


async def main():
    await plugin_manager.register(GoodPlugin())
    await plugin_manager.register(BadPlugin())
    log.info("Registered plugins: %s", [p.name for p in plugin_manager.plugins])

    ctx = PluginContext(
        slug="dev", method="call_tool", tool_name="search_issues",
        arguments={}, server_id="srv-1",
    )

    # Both plugins should fire. BadPlugin raises, but GoodPlugin still runs.
    await plugin_manager.execute("on_before_tool_call", ctx=ctx)
    log.info("GoodPlugin ran: %s", ctx.extra.get("good_ran", False))

    mock_result = {"content": [{"type": "text", "text": "OK"}], "isError": False}
    ctx.extra["duration_ms"] = 500.0
    await plugin_manager.execute("on_after_tool_call", ctx=ctx, result=mock_result)

    log.info("Example completed — app did NOT crash despite BadPlugin error")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
