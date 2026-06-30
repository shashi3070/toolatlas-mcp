# Governance ABAC Plugin

Attribute-Based Access Control (ABAC) plugin that restricts tool access
per organization. Demonstrates PluginAbortError, PluginContext identity
fields (org_id, user_id), priority ordering, and the on_tool_filter hook.

## Running

```bash
python examples/plugins/governance_abac.py
```

## What It Demonstrates

- PluginAbortError to block unauthorized tool calls
- PluginContext.org_id for per-tenant authorization
- on_tool_filter to hide sensitive tools from unauthorized callers
- Priority ordering (runs before other plugins)
"""

import logging
import sys

from toolatlas_mcp.plugin import Plugin, PluginAbortError, PluginContext, plugin_manager

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


SENSITIVE_TOOLS = {"delete_repo", "delete_database", "admin_exec"}

ALLOWED_TOOLS = {
    "acme-corp": {"search", "read", "list", "create_issue", "search_issues"},
    "other-corp": {"slack_send", "search"},
}


class GovernanceABACPlugin(Plugin):
    name = "governance"
    priority = -50  # runs before metrics and rate limiters

    @staticmethod
    def _org_identifier(ctx: PluginContext) -> str:
        return ctx.org_id or ctx.tenant_id or "anonymous"

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        org_id = self._org_identifier(ctx)
        allowed = ALLOWED_TOOLS.get(org_id, set())
        if ctx.tool_name not in allowed:
            raise PluginAbortError(
                f"Org '{org_id}' not authorized for tool '{ctx.tool_name}'"
            )
        log.info("ABAC: %s allowed for org '%s'", ctx.tool_name, org_id)

    async def on_tool_filter(self, ctx: PluginContext, tools: list[dict]) -> list[dict]:
        org_id = self._org_identifier(ctx)
        return [t for t in tools if t["name"] not in SENSITIVE_TOOLS or org_id == "admin"]


plugin = GovernanceABACPlugin()


async def main():
    log.info("Registering GovernanceABACPlugin (priority=%d)...", plugin.priority)
    await plugin_manager.register(plugin)

    # Test 1: authorized tool call
    ctx = PluginContext(
        slug="dev", method="call_tool", tool_name="search_issues",
        arguments={"query": "bug"},
        org_id="acme-corp", user_id="shashi",
    )
    try:
        await plugin_manager.execute("on_before_tool_call", ctx=ctx)
        log.info("Test 1 PASS: authorized call allowed")
    except PluginAbortError as e:
        log.error("Test 1 FAIL: %s", e)

    # Test 2: unauthorized tool call
    ctx.tool_name = "delete_repo"
    try:
        await plugin_manager.execute("on_before_tool_call", ctx=ctx)
        log.error("Test 2 FAIL: should have been blocked!")
    except PluginAbortError as e:
        log.info("Test 2 PASS: unauthorized call blocked — %s", e)

    # Test 3: tool filter hides sensitive tools
    all_tools = [
        {"name": "search_issues"},
        {"name": "delete_repo"},
        {"name": "list_projects"},
    ]
    ctx2 = PluginContext(org_id="acme-corp")
    filtered = await plugin.on_tool_filter(ctx2, all_tools)
    names = [t["name"] for t in filtered]
    assert "delete_repo" not in names, "Sensitive tool should be hidden"
    assert "search_issues" in names, "Safe tool should remain"
    log.info("Test 3 PASS: tool filter hid sensitive tools: %s", names)

    log.info("Example completed successfully")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
