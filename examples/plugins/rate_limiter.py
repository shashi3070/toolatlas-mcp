# Rate Limiter Plugin

Limits tool calls to a maximum per minute, per tool.

## Running

```bash
python examples/plugins/rate_limiter.py
```

## What It Demonstrates

- In-memory state tracking across calls
- Per-tool rate limiting with sliding window
- Rejecting calls that exceed the threshold
"""

import logging
import time
from collections import defaultdict

from toolatlas_mcp.plugin import Plugin, PluginAbortError, PluginContext, plugin_manager

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


class RateLimiterPlugin(Plugin):
    name = "rate_limiter"

    def __init__(self, max_calls: int = 5, window_sec: int = 60):
        self.max_calls = max_calls
        self.window_sec = window_sec
        self._call_times: dict[str, list[float]] = defaultdict(list)

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        now = time.time()
        cutoff = now - self.window_sec
        tool = ctx.tool_name

        self._call_times[tool] = [t for t in self._call_times[tool] if t > cutoff]

        if len(self._call_times[tool]) >= self.max_calls:
            raise PluginAbortError(
                f"Rate limit exceeded for '{tool}': "
                f"{self.max_calls} calls per {self.window_sec}s"
            )

        self._call_times[tool].append(now)
        remaining = self.max_calls - len(self._call_times[tool])
        log.info("Rate limit: %s has %d calls remaining", tool, remaining)


plugin = RateLimiterPlugin(max_calls=3, window_sec=60)


async def main():
    await plugin_manager.register(plugin)
    log.info("Rate limit: max %d calls per %ds", plugin.max_calls, plugin.window_sec)

    ctx = PluginContext(
        slug="dev", method="call_tool", tool_name="search_issues",
        arguments={},
    )

    for i in range(5):
        try:
            await plugin_manager.execute("on_before_tool_call", ctx=ctx)
            log.info("Call %d: allowed", i + 1)
        except RuntimeError as e:
            log.info("Call %d: blocked — %s", i + 1, e)

    log.info("Example completed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
