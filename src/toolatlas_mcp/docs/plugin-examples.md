# Plugin System — Examples & Scenarios

This document contains complete, runnable plugin examples, real-world scenarios,
and documented corner cases.

See [plugin-system.md](plugin-system.md) for the base class and hook signatures.
See [plugin-loading.md](plugin-loading.md) for how to register these plugins.

## 1. Built-in Plugins

### CachePlugin (`plugin/builtins/cache.py`)

Two-tier cache: **in-process memory** → **Redis** (optional).

```python
class CachePlugin(Plugin):
    name = "cache"

    async def on_before_cache_lookup(self, slug: str) -> tuple[float, list] | None:
        # 1. Check in-memory dict (local TTL: 60s)
        # 2. If miss, check Redis (when configured)
        # 3. Return (timestamp, tools) or None

    async def on_after_cache_lookup(self, slug: str, tools: list) -> None:
        # Write to both memory and Redis
        # Redis TTL from settings.cache_ttl (default 300s)

    async def on_cache_invalidated(self, slug: str) -> None:
        # Remove from both tiers
```

Key design decisions:
- `CachePlugin:32` — `_memory` dict uses a short local TTL (60s) so a single process
  doesn't hold stale data too long, while Redis carries the full TTL (300s)
- `CachePlugin:47-48` — Graceful degradation: if Redis is configured but unreachable,
  falls back to memory-only with a log warning
- `CachePlugin:84-85` — Module-level `plugin = CachePlugin()` for entry-point loading

### MetricsPlugin (`plugin/builtins/metrics.py`)

Collects tool call counts, durations (p50/p95/p99), cache hit ratios, and exposes a
`GET /metrics` endpoint via a FastAPI `APIRouter`.

```python
class MetricsPlugin(Plugin):
    name = "metrics"

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        ctx.extra["start_time"] = time.time()  # inject start time

    async def on_after_tool_call(self, ctx: PluginContext, result: dict) -> None:
        self._call_count[ctx.tool_name] += 1
        dur = ctx.extra.get("duration_ms", 0)
        if dur:
            self._durations[ctx.tool_name].append(dur)

    @property
    def router(self) -> APIRouter:
        r = APIRouter()
        @r.get("/metrics")
        async def metrics():
            return self._render_prometheus()
        return r
```

The `router` property returns a FastAPI `APIRouter` — a pattern plugins can use to
contribute their own HTTP endpoints. The app would mount this at startup.

## 2. Quickstart: AuditLoggerPlugin

A minimal but complete plugin that logs every tool call:

```python
# my_audit_plugin/plugin.py
import json
import logging
from toolatlas_mcp.plugin import Plugin, PluginContext

log = logging.getLogger(__name__)

class AuditLoggerPlugin(Plugin):
    name = "audit_logger"

    async def startup(self):
        log.info("AuditLoggerPlugin started")

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        log.info("%s called %s with %s", ctx.slug, ctx.tool_name, ctx.arguments)

    async def on_after_tool_call(self, ctx: PluginContext, result: dict) -> None:
        with open("audit.log", "a") as f:
            f.write(json.dumps({
                "slug": ctx.slug,
                "tool": ctx.tool_name,
                "duration_ms": ctx.extra.get("duration_ms"),
                "success": not result.get("isError"),
            }) + "\n")

# Required for entry-point loading:
plugin = AuditLoggerPlugin()
```

## 3. Complete Example: Email Notification Plugin

This plugin sends an email for **every hook event** in the system. It uses
Python's standard-library `smtplib` — no external dependencies.

```python
# email_notifier/plugin.py
import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Any

from toolatlas_mcp.plugin import Plugin, PluginContext

log = logging.getLogger(__name__)


def _send(subject: str, body: str):
    """Synchronous helper — runs inside the async hook via asyncio.to_thread."""
    host = os.environ.get("SMTP_HOST", "localhost")
    port = int(os.environ.get("SMTP_PORT", "25"))
    sender = os.environ.get("SMTP_SENDER", "toolatlas@localhost")
    recipient = os.environ.get("SMTP_RECIPIENT", "admin@localhost")

    msg = EmailMessage()
    msg["Subject"] = f"[ToolAtlas] {subject}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.send_message(msg)
        log.info("Email sent: %s", subject)
    except Exception as e:
        log.warning("Email send failed (%s): %s", subject, e)


class EmailNotifierPlugin(Plugin):
    name = "email_notifier"

    async def startup(self):
        import asyncio
        await asyncio.to_thread(
            _send, "Plugin Started",
            "The EmailNotifierPlugin has been registered.",
        )

    async def shutdown(self):
        import asyncio
        await asyncio.to_thread(
            _send, "Plugin Stopped",
            "The EmailNotifierPlugin is shutting down.",
        )

    async def on_before_list_tools(self, ctx: PluginContext) -> list[dict] | None:
        import asyncio
        await asyncio.to_thread(
            _send, "List Tools (before)",
            f"Proxy '{ctx.slug}' is about to list tools.\nMethod: {ctx.method}",
        )
        return None

    async def on_after_list_tools(self, ctx: PluginContext, tools: list[dict]) -> None:
        import asyncio
        tool_names = [t.get("name", "?") for t in tools]
        await asyncio.to_thread(
            _send, "List Tools (after)",
            f"Proxy '{ctx.slug}' listed {len(tools)} tools:\n"
            f"{chr(10).join('  - ' + n for n in tool_names)}",
        )

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        import asyncio
        await asyncio.to_thread(
            _send, f"Call Tool: {ctx.tool_name}",
            f"Proxy: {ctx.slug}\nTool:  {ctx.tool_name}\n"
            f"Server: {ctx.server_id}\nArguments:\n{_fmt_dict(ctx.arguments)}",
        )

    async def on_after_tool_call(self, ctx: PluginContext, result: dict) -> None:
        import asyncio
        success = not result.get("isError", False)
        dur = ctx.extra.get("duration_ms", 0)
        await asyncio.to_thread(
            _send, f"Tool Result: {ctx.tool_name}",
            f"Proxy: {ctx.slug}\nTool:  {ctx.tool_name}\n"
            f"Duration: {dur:.0f}ms\nSuccess:  {success}\n"
            f"Result preview:\n{_fmt_dict(result)[:2000]}",
        )

    async def on_server_connected(self, server_id: str) -> None:
        import asyncio
        await asyncio.to_thread(_send, "Server Connected", f"Server ID: {server_id}")

    async def on_server_disconnected(self, server_id: str) -> None:
        import asyncio
        await asyncio.to_thread(_send, "Server Disconnected", f"Server ID: {server_id}")

    async def on_tool_added(self, server_id: str, tool_names: list[str]) -> None:
        import asyncio
        await asyncio.to_thread(
            _send, f"Tools Added ({len(tool_names)})",
            f"Server: {server_id}\nNew tools:\n{chr(10).join('  - ' + n for n in tool_names)}",
        )

    async def on_tool_updated(self, server_id: str, tool_names: list[str]) -> None:
        import asyncio
        await asyncio.to_thread(
            _send, f"Tools Updated ({len(tool_names)})",
            f"Server: {server_id}\nUpdated:\n{chr(10).join('  - ' + n for n in tool_names)}",
        )

    async def on_tool_removed(self, server_id: str, tool_names: list[str]) -> None:
        import asyncio
        await asyncio.to_thread(
            _send, f"Tools Removed ({len(tool_names)})",
            f"Server: {server_id}\nRemoved:\n{chr(10).join('  - ' + n for n in tool_names)}",
        )

    async def on_before_cache_lookup(self, slug: str) -> tuple[float, list] | None:
        import asyncio
        await asyncio.to_thread(_send, "Cache Lookup (before)", f"Proxy '{slug}' is checking cache.")
        return None

    async def on_after_cache_lookup(self, slug: str, tools: list) -> None:
        import asyncio
        await asyncio.to_thread(
            _send, "Cache Lookup (after)",
            f"Proxy '{slug}' cache resolved ({len(tools)} tools).",
        )

    async def on_cache_invalidated(self, slug: str) -> None:
        import asyncio
        await asyncio.to_thread(_send, "Cache Invalidated", f"Proxy '{slug}' tools cache was cleared.")


def _fmt_dict(d: dict[str, Any], indent: int = 2) -> str:
    import json
    return json.dumps(d, indent=indent, default=str, ensure_ascii=False)


plugin = EmailNotifierPlugin()
```

### Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `SMTP_HOST` | `localhost` | SMTP server address |
| `SMTP_PORT` | `25` | SMTP server port |
| `SMTP_SENDER` | `toolatlas@localhost` | From address |
| `SMTP_RECIPIENT` | `admin@localhost` | To address |

### Testing with a debug SMTP server

```bash
# Terminal 1: fake SMTP server that prints emails to stdout
python -m smtpd -c DebuggingServer -n localhost:1025

# Terminal 2: start ToolAtlas with debug port
SMTP_HOST=localhost SMTP_PORT=1025 SMTP_RECIPIENT=me@example.com \
  uvicorn toolatlas_mcp.api.app:app
```

## 4. Real-World Scenarios

### Scenario A: Audit Trail for Compliance

Log every tool call to a structured file for compliance auditing:

```python
import json, csv, logging
from pathlib import Path
from toolatlas_mcp.plugin import Plugin, PluginContext

log = logging.getLogger(__name__)

class ComplianceAuditPlugin(Plugin):
    name = "compliance_audit"

    def __init__(self, log_dir: str = "/var/log/toolatlas"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        entry = {
            "event": "tool_call_started",
            "proxy": ctx.slug,
            "tool": ctx.tool_name,
            "args_keys": list(ctx.arguments.keys()),
            "server_id": ctx.server_id,
        }
        self._write(entry)

    async def on_after_tool_call(self, ctx: PluginContext, result: dict) -> None:
        entry = {
            "event": "tool_call_completed",
            "proxy": ctx.slug,
            "tool": ctx.tool_name,
            "duration_ms": ctx.extra.get("duration_ms"),
            "is_error": result.get("isError", False),
        }
        self._write(entry)

    def _write(self, entry: dict):
        with open(self.log_dir / "compliance.log", "a") as f:
            f.write(json.dumps(entry) + "\n")
```

### Scenario B: Argument Validation

Block tool calls with invalid or missing arguments before they reach the upstream server:

```python
class ValidationPlugin(Plugin):
    name = "validator"

    REQUIRED_ARGS = {
        "delete_repo": ["name"],
        "create_issue": ["project", "summary"],
    }

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        required = self.REQUIRED_ARGS.get(ctx.tool_name, [])
        missing = [k for k in required if k not in ctx.arguments]
        if missing:
            raise ValueError(
                f"Tool '{ctx.tool_name}' missing required arguments: {missing}"
            )

        # Type validation
        if ctx.tool_name == "create_repo":
            if not isinstance(ctx.arguments.get("name"), str):
                raise TypeError("'name' must be a string")
```

### Scenario C: Rate Limiting per Tool

Track calls per tool and reject calls that exceed a threshold:

```python
import time
from collections import defaultdict

class RateLimiterPlugin(Plugin):
    name = "rate_limiter"

    def __init__(self, max_calls: int = 10, window_sec: int = 60):
        self.max_calls = max_calls
        self.window_sec = window_sec
        self._call_times: dict[str, list[float]] = defaultdict(list)

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        now = time.time()
        window_start = now - self.window_sec
        tool = ctx.tool_name

        self._call_times[tool] = [t for t in self._call_times[tool] if t > window_start]
        if len(self._call_times[tool]) >= self.max_calls:
            raise RuntimeError(
                f"Rate limit exceeded for '{tool}': "
                f"{self.max_calls} calls per {self.window_sec}s"
            )
        self._call_times[tool].append(now)

    async def on_after_tool_call(self, ctx: PluginContext, result: dict) -> None:
        pass  # Rate limit already enforced in before hook
```

### Scenario D: Description Enrichment Plugin

Append usage guidelines or policy warnings to tool descriptions:

```python
class EnrichmentPlugin(Plugin):
    name = "enricher"

    POLICY_WARNINGS = {
        "delete_repo": "WARNING: This action is irreversible. Ensure you have backups.",
        "resolve_incident": "Only use after confirming the incident is truly resolved.",
    }

    async def on_after_list_tools(self, ctx: PluginContext, tools: list[dict]) -> None:
        for tool in tools:
            warning = self.POLICY_WARNINGS.get(tool["name"])
            if warning:
                tool["description"] = f"{tool['description']}\n\n{warning}"
```

### Scenario E: Error Recovery Plugin

Automatically retry on transient failures:

```python
import asyncio

class RetryPlugin(Plugin):
    name = "retry"

    def __init__(self, max_retries: int = 3, delay_sec: float = 1.0):
        self.max_retries = max_retries
        self.delay_sec = delay_sec

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        ctx.extra["retry_count"] = 0

    async def on_after_tool_call(self, ctx: PluginContext, result: dict) -> None:
        if result.get("isError"):
            retries = ctx.extra.get("retry_count", 0)
            if retries < self.max_retries:
                await asyncio.sleep(self.delay_sec * (retries + 1))
                ctx.extra["retry_count"] = retries + 1
                # Note: actual retry invocation would need to be handled
                # by the engine or middleware, not from the plugin alone.
```

## 5. Corner Cases

### Case 1: Plugin raises in `on_before_tool_call`

```python
class CrashPlugin(Plugin):
    name = "crash"

    async def on_before_tool_call(self, ctx: PluginContext):
        raise RuntimeError("Unexpected failure")
```

**What happens:** The error is caught by `PluginManager.execute()` at `manager.py:82-83`,
logged as `ERROR Plugin crash hook on_before_tool_call error: ...`, and execution
continues with the next plugin. The tool call itself proceeds unless **all** plugins
that could block have been skipped.

### Case 2: Two plugins modify the same description

```python
class PrefixPlugin(Plugin):
    name = "prefix"
    async def on_after_list_tools(self, ctx, tools):
        for t in tools:
            t["description"] = "[PREFIX] " + t["description"]

class SuffixPlugin(Plugin):
    name = "suffix"
    async def on_after_list_tools(self, ctx, tools):
        for t in tools:
            t["description"] = t["description"] + " [SUFFIX]"
```

**Order guarantee:** Plugins execute in registration order. If `PrefixPlugin` is
registered first, the result is `[PREFIX] original [SUFFIX]`.

### Case 3: Plugin takes too long

Plugin hooks execute within the async event loop. A slow hook blocks the entire
tool call or listing for all clients. The engine does **not** apply a timeout to
plugin hooks (only to the upstream MCP server call, which times out at 30s).

**Recommendation:** Use `asyncio.wait_for()` inside any hook that might block:

```python
async def on_before_tool_call(self, ctx: PluginContext):
    result = await asyncio.wait_for(
        self._expensive_operation(), timeout=5.0,
    )
```

### Case 4: Plugin registered twice

Registering the same plugin instance twice causes its hooks to fire twice.

```python
p = MyPlugin()
await plugin_manager.register(p)
await plugin_manager.register(p)  # Same instance — duplicate hooks
# → on_before_tool_call fires twice, both times on the same instance
```

**Fix:** Check `plugin_manager.plugins` before registering, or use a set:

```python
if not any(p.name == "my_plugin" for p in plugin_manager.plugins):
    await plugin_manager.register(MyPlugin())
```

### Case 5: Empty plugin with no hooks

```python
class NoOpPlugin(Plugin):
    name = "noop"
```

A plugin with no hook overrides is valid. It registers, `startup()` is called
(the base no-op), and it never triggers during execution. This can be useful as
a stub for testing or for plugins that only contribute HTTP routes via `router`.

### Case 6: Plugin mutates arguments

Arguments in `PluginContext` are passed by reference. A mutation in `on_before_tool_call`
propagates to the engine:

```python
class MutatorPlugin(Plugin):
    name = "mutator"
    async def on_before_tool_call(self, ctx: PluginContext):
        ctx.arguments["injected"] = "hacked value"
```

The upstream server receives the modified arguments. **Be careful**: mutations are
visible to later plugins and to the engine itself.

### Case 7: Short-circuit + `on_after` both registered

The `on_before_cache_lookup` hook can short-circuit via `execute_first`. If it returns
non-None, the normal `list_tools` flow (and hence `on_after_list_tools`) is skipped.
However, `on_after_cache_lookup` still fires because it's in the `proxy_message()`
handler after the cache-or-engine branch.

```
Cache hit path:
  on_before_cache_lookup (short-circuit) → on_after_cache_lookup → send tools
  (on_after_list_tools is NOT called)

Cache miss path:
  on_before_cache_lookup (returns None) → engine.list_tools() →
    on_after_list_tools (inside engine) → on_after_cache_lookup → send tools
```
