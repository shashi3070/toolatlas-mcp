# Validation Plugin

Validates tool arguments in `on_before_tool_call` before they reach the upstream server.

## Running

```bash
python examples/plugins/validation_plugin.py
```

## What It Demonstrates

- Rejecting calls with missing required arguments
- Type validation on arguments
- The `raise`-to-block pattern in `on_before_tool_call`
"""

import logging
import sys

from toolatlas_mcp.plugin import Plugin, PluginAbortError, PluginContext, plugin_manager

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


class ValidationPlugin(Plugin):
    name = "validator"

    REQUIRED_ARGS = {
        "delete_repo": ["name"],
        "create_issue": ["project", "summary"],
    }

    TYPE_CHECKS = {
        "create_repo": {"name": str},
        "create_issue": {"project": str, "summary": str},
    }

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        tool = ctx.tool_name
        args = ctx.arguments

        required = self.REQUIRED_ARGS.get(tool, [])
        missing = [k for k in required if k not in args]
        if missing:
            msg = f"Tool '{tool}' missing required arguments: {missing}"
            log.error(msg)
            raise PluginAbortError(msg)

        type_map = self.TYPE_CHECKS.get(tool, {})
        for key, expected_type in type_map.items():
            if key in args and not isinstance(args[key], expected_type):
                msg = f"Tool '{tool}' argument '{key}' must be {expected_type.__name__}, got {type(args[key]).__name__}"
                log.error(msg)
                raise PluginAbortError(msg)

        log.info("Validation passed for %s/%s", ctx.slug, tool)


plugin = ValidationPlugin()


async def main():
    log.info("Registering ValidationPlugin...")
    await plugin_manager.register(plugin)

    ctx = PluginContext(
        slug="dev", method="call_tool", tool_name="create_issue",
        arguments={"project": "TOOLATLAS"},
    )

    # This should raise PluginAbortError because "summary" is missing
    try:
        await plugin_manager.execute("on_before_tool_call", ctx=ctx)
        log.info("ERROR: Should have raised PluginAbortError!")
    except PluginAbortError as e:
        log.info("Correctly blocked: %s", e)

    # Fix arguments and try again
    ctx.arguments["summary"] = "Fix the bug"
    try:
        await plugin_manager.execute("on_before_tool_call", ctx=ctx)
        log.info("Validation passed with complete arguments")
    except PluginAbortError as e:
        log.error("Unexpected error: %s", e)

    log.info("Example completed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
