# Basic Audit Logger Plugin

Minimal plugin that logs every tool call to a file and via Python logger.

## Running

```bash
python examples/plugins/basic_audit_logger.py
```

## What It Demonstrates

- Plugin class with `name` attribute
- `on_before_tool_call` hook — log incoming call
- `on_after_tool_call` hook — write structured audit log
- Registration via `plugin_manager.register()`
- Manual hook execution with `PluginContext`
"""

import json
import logging
import sys

from toolatlas_mcp.plugin import Plugin, PluginContext, plugin_manager

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


class AuditLoggerPlugin(Plugin):
    name = "audit_logger"

    async def startup(self):
        log.info("AuditLoggerPlugin started")

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        log.info(
            "%s called %s with args: %s",
            ctx.slug, ctx.tool_name, list(ctx.arguments.keys()),
        )

    async def on_after_tool_call(self, ctx: PluginContext, result: dict) -> None:
        entry = {
            "slug": ctx.slug,
            "tool": ctx.tool_name,
            "duration_ms": ctx.extra.get("duration_ms"),
            "success": not result.get("isError", False),
        }
        with open("/tmp/audit.log", "a") as f:
            f.write(json.dumps(entry) + "\n")
        log.info("Logged audit entry for %s/%s", ctx.slug, ctx.tool_name)


plugin = AuditLoggerPlugin()


async def main():
    log.info("Registering AuditLoggerPlugin...")
    await plugin_manager.register(plugin)
    log.info("Registered plugins: %s", [p.name for p in plugin_manager.plugins])

    # Simulate a tool call to see hooks fire
    ctx = PluginContext(
        slug="dev",
        method="call_tool",
        tool_name="search_issues",
        arguments={"jql": "project = TOOLATLAS"},
        server_id="server-123",
    )
    ctx.extra["duration_ms"] = 1520.4

    log.info("Executing on_before_tool_call...")
    await plugin_manager.execute("on_before_tool_call", ctx=ctx)

    mock_result = {"content": [{"type": "text", "text": "Found 3 issues"}], "isError": False}
    log.info("Executing on_after_tool_call...")
    await plugin_manager.execute("on_after_tool_call", ctx=ctx, result=mock_result)

    # Show the audit log
    try:
        with open("/tmp/audit.log") as f:
            log.info("Audit log contents:\n%s", f.read())
    except FileNotFoundError:
        log.warning("Audit log file not found (expected on Windows: check /tmp/)")

    log.info("Example completed successfully")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
