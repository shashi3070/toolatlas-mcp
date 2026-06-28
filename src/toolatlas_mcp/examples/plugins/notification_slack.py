# Slack Notification Plugin

Sends a Slack webhook on every tool call event.

## Running

```bash
# Requires SLACK_WEBHOOK_URL environment variable
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
python examples/plugins/notification_slack.py
```

## What It Demonstrates

- Environment-based configuration
- HTTP POST to external service (via `httpx`)
- Both `on_before_tool_call` and `on_after_tool_call` hooks
- Graceful handling of external service failures (no crash if Slack is down)
"""

import logging
import os

from toolatlas_mcp.plugin import Plugin, PluginContext, plugin_manager

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


class SlackNotifierPlugin(Plugin):
    name = "slack_notifier"

    def __init__(self):
        self._webhook_url = SLACK_WEBHOOK_URL
        if self._webhook_url:
            log.info("SlackNotifierPlugin: webhook URL configured")
        else:
            log.warning("SlackNotifierPlugin: SLACK_WEBHOOK_URL not set — notifications disabled")

    async def _send_slack(self, text: str) -> None:
        if not self._webhook_url:
            return
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(self._webhook_url, json={"text": text}, timeout=10)
            log.info("Slack notification sent")
        except Exception as e:
            log.warning("Slack notification failed: %s", e)

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        text = (
            f":toolatlas: Tool call started\n"
            f"• *Proxy:* {ctx.slug}\n"
            f"• *Tool:* `{ctx.tool_name}`\n"
            f"• *Arguments:* `{dict(ctx.arguments)}`"
        )
        await self._send_slack(text)

    async def on_after_tool_call(self, ctx: PluginContext, result: dict) -> None:
        success = not result.get("isError", False)
        dur = ctx.extra.get("duration_ms", 0)
        status = ":white_check_mark:" if success else ":x:"
        text = (
            f"{status} Tool call completed\n"
            f"• *Proxy:* {ctx.slug}\n"
            f"• *Tool:* `{ctx.tool_name}`\n"
            f"• *Duration:* {dur:.0f}ms\n"
            f"• *Success:* {success}"
        )
        await self._send_slack(text)


plugin = SlackNotifierPlugin()


async def main():
    if not SLACK_WEBHOOK_URL:
        log.warning("SLACK_WEBHOOK_URL not set — running in dry-run mode")

    await plugin_manager.register(plugin)
    log.info("Registered plugins: %s", [p.name for p in plugin_manager.plugins])

    ctx = PluginContext(
        slug="dev", method="call_tool", tool_name="search_issues",
        arguments={"jql": "status = Open"}, server_id="srv-1",
    )
    ctx.extra["duration_ms"] = 1234.5

    await plugin_manager.execute("on_before_tool_call", ctx=ctx)

    mock_result = {"content": [{"type": "text", "text": "Found 5 issues"}], "isError": False}
    await plugin_manager.execute("on_after_tool_call", ctx=ctx, result=mock_result)

    log.info("Example completed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
