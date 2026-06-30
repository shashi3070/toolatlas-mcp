# Plugin Architecture v2 — Abort, Governance, Session Tracing & Multi-Tenancy

## 1. `PluginAbortError` — Clean Plugin Abort

### Problem

`PluginManager.execute()` and `execute_first()` catch ALL exceptions (lines 82-83, 96-97),
making `on_before_tool_call` and `on_before_list_tools` unusable for authorization,
rate limiting, or any blocking logic. Every plugin that needs to deny a request
is broken by design — the exception is logged and swallowed.

### Solution

Add `PluginAbortError` as a public exception in the Plugin API. It propagates
through the manager while all other exceptions are still caught and logged.

```python
# plugin/base.py
class PluginAbortError(Exception):
    """Raise from on_before_tool_call / on_before_list_tools to abort the
    operation. execute() propagates this; all other exceptions are still
    caught, logged, and swallowed."""
```

### Manager Changes

```python
# plugin/manager.py — execute()
except PluginAbortError:
    raise              # ← abort signals propagate
except Exception as e:
    log.error(...)     # ← unexpected bugs still swallowed
```

Same pattern in `execute_first()`.

### Engine Changes

```python
# proxy/engine.py — call_tool()
try:
    await plugin_manager.execute("on_before_tool_call", ctx=pctx)
except PluginAbortError as e:
    raise PermissionError(str(e)) from e

# proxy/engine.py — list_tools()
try:
    short_circuit = await plugin_manager.execute_first("on_before_list_tools", ctx=ctx)
except PluginAbortError as e:
    raise PermissionError(str(e)) from e
```

`PermissionError` already maps to MCP error code `-32001` in `server.py:268-270`.

### Backward Compatibility

Every existing plugin keeps working because none of them raise
`PluginAbortError`. The example plugins that currently raise `RuntimeError`
or `ValueError` (rate_limiter, validation_plugin) are updated to use the
proper exception.

---

## 2. Session Tracing — `trace_id`, `span_id`, `parent_span_id`

### Problem

The call record only stores `trace_id`. When a client passes the same
`trace_id` for multiple calls in a session (e.g., a chatbot conversation),
the graph endpoint correctly groups them, but there is no way to represent
parent-child relationships between calls. Additionally, each call needs a
unique `span_id` so the graph can distinguish individual calls within a
trace.

### The `_meta` Protocol

Clients pass tracing and tenant context in the `_meta` field of every
`tools/call` JSON-RPC request:

```json
{
    "method": "tools/call",
    "params": {
        "name": "search_issues",
        "arguments": {"query": "bug"},
        "_meta": {
            "trace_id": "session-abc-123",
            "span_id": "call-0003",
            "parent_span_id": "call-0001",
            "org_id": "acme-corp",
            "tenant_id": "dev-team-42",
            "user_id": "shashi",
            "client_id": "chatbot-v3"
        }
    }
}
```

### Field Reference

| Field | If passed | If omitted | Always stored? |
|-------|-----------|------------|----------------|
| `trace_id` | Used as-is | Auto-generated via `uuid4()` | Yes — non-null |
| `span_id` | Used as-is | Auto-generated via `uuid4()` | Yes — non-null |
| `parent_span_id` | Stored for hierarchy | Null (top-level call) | Yes — nullable |
| `org_id` | Stored for filtering | Null | Yes — nullable |
| `tenant_id` | Stored for filtering | Null | Yes — nullable |
| `user_id` | Stored for context | Null | Yes — nullable |
| `client_id` | Stored for context | Null | Yes — nullable |

**Rule**: `span_id` is always set — if the client does not pass one,
ToolAtlas generates one. Every call record always has both `trace_id` and
`span_id` populated.

### End-to-End Flow

```
Client (chatbot)
  │  tools/call {"_meta": {
  │    "trace_id": "sess-abc",
  │    "span_id": "call-003",
  │    "parent_span_id": "call-002",
  │    "org_id": "acme-corp",
  │    "tenant_id": "dev-42",
  │    "user_id": "shashi",
  │    "client_id": "chatbot-v3"
  │  }}
  ▼
server.py
  params = body.get("params", {})
  meta = params.get("_meta", {})          ← extracts full _meta dict
  result = await engine.call_tool(slug, name, arguments, meta=meta)
  ▼
engine.py (call_tool)
  trace_id = (meta or {}).get("trace_id")
  span_id = (meta or {}).get("span_id")
  parent_span_id = (meta or {}).get("parent_span_id")
  org_id = (meta or {}).get("org_id")
  tenant_id = (meta or {}).get("tenant_id")
  user_id = (meta or {}).get("user_id")
  client_id = (meta or {}).get("client_id")
  
  # Populate PluginContext
  pctx.client_id = client_id
  pctx.user_id = user_id
  pctx.org_id = org_id
  pctx.tenant_id = tenant_id
  pctx.meta = meta

  # Call middleware
  async with self.middleware.track(
      trace_id=trace_id,
      span_id=span_id,
      parent_span_id=parent_span_id,
      org_id=org_id,
      tenant_id=tenant_id,
      user_id=user_id,
      client_id=client_id,
      ...
  ) as ctx:
      ...
      # Forward to upstream MCP
      result = await client.call_tool(name, arguments, meta=meta)
  ▼
middleware.py (track)
  trace_id = trace_id or str(uuid4())
  span_id = span_id or str(uuid4())
  storage.record_call(
      trace_id=trace_id,
      span_id=span_id,
      parent_span_id=parent_span_id,
      org_id=org_id,
      tenant_id=tenant_id,
      user_id=user_id,
      client_id=client_id,
      ...
  )
  ▼
storage.record_call()  →  stored in JSON / SQLite / Postgres
  ▼
upstream MCP server receives full _meta in tools/call
```

### Storage Changes

```python
# registry/storage.py (abstract)
async def record_call(
    self,
    ...,
    trace_id: str | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    org_id: str | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
    client_id: str | None = None,
    ...
) -> Any:
```

Both `json_storage.py` and `repository.py` store all new fields. The
`repository.py` also adds columns to the `ToolCall` SQLAlchemy model.

### Graph / Trace View Changes

`GET /api/graph/trace/{trace_id}` builds a span tree instead of a flat
sequential list:

```
Before (sequential):
  call-001 ──→ call-002 ──→ call-003 ──→ call-004

After (span tree with parent_span_id):
  call-001 ──→ call-002 ──→ call-003
       │
       └── call-004
```

- Calls with `parent_span_id=null` are root nodes
- Calls with `parent_span_id="xxx"` are child edges from "xxx"
- Edge rendering in vis-network uses `arrows: "to"` pointing parent → child

### Client Example

```python
# examples/client/python_client.py (new section)
session_trace_id = str(uuid4())
span_counter = 0

for tool_name, args in session_tools:
    meta = {
        "trace_id": session_trace_id,
        "span_id": f"call-{span_counter:04d}",
        "parent_span_id": None,       # top-level
        "org_id": "acme-corp",
        "tenant_id": "dev-42",
        "user_id": "shashi",
        "client_id": "my-chatbot",
    }
    result = await client.call_tool(slug, tool_name, args, meta=meta)
    span_counter += 1
```

---

## 3. `PluginContext` Identity Fields — Auth, Governance & Multi-Tenancy

### Problem

`PluginContext` lacks caller identity, tenant context, and routing
information, making it impossible to write authorization, audit, or
per-tenant governance plugins.

### Current Fields

```python
@dataclass
class PluginContext:
    slug: str = ""
    method: str = ""
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    server_id: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
```

### Added Fields

```python
@dataclass
class PluginContext:
    ...
    # Identity
    client_id: str | None = None       # caller (e.g. "chatbot-v3")
    user_id: str | None = None         # authenticated user
    org_id: str | None = None          # organization
    tenant_id: str | None = None       # tenant within org

    # Routing
    proxy_id: str | None = None        # proxy that received the call
    proxy_name: str | None = None
    server_name: str | None = None

    # Raw metadata
    meta: dict[str, Any] = field(default_factory=dict)  # full _meta from request
```

### How Plugins Use These

```python
# Governance plugin — per-tenant tool access
class GovernancePlugin(Plugin):
    name = "governance"
    priority = -50

    ALLOWED = {
        "acme-corp": {"search", "read"},
        "other-corp": {"slack_send"},
    }

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        allowed = self.ALLOWED.get(ctx.org_id, set())
        if ctx.tool_name not in allowed:
            raise PluginAbortError(
                f"Org '{ctx.org_id}' not authorized for '{ctx.tool_name}'"
            )


# Audit plugin — log all calls per tenant
class AuditPlugin(Plugin):
    name = "audit"

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        log.info(
            "Tool call: org=%s tenant=%s user=%s tool=%s args=%s",
            ctx.org_id, ctx.tenant_id, ctx.user_id,
            ctx.tool_name, ctx.arguments,
        )


# Rate limiter — per-tenant limits
class RateLimiterPlugin(Plugin):
    name = "rate_limiter"

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        key = f"{ctx.org_id}:{ctx.tool_name}"
        if self._is_rate_limited(key):
            raise PluginAbortError(f"Rate limit exceeded for {key}")
```

### Construction Sites

| Location | What's Available |
|----------|-----------------|
| `engine.py` (call_tool) | `proxy["id"]`, `proxy["name"]`, `server["name"]`, full `meta` |
| `engine.py` (list_tools) | `proxy["id"]`, `proxy["name"]` |
| `server.py` (list_tools handler) | `slug` → proxy lookup |

---

## 4. Tenant Multi-Tenancy Design

### Approach: Pass-through Storage + Plugin Validation

ToolAtlas does **not** enforce tenant isolation at the storage layer.
Instead:

1. **Store everything** — all `_meta` fields (`org_id`, `tenant_id`, etc.)
   are stored verbatim on every call record.
2. **Let plugins validate** — governance/authorization plugins inspect
   `PluginContext.tenant_id` / `.org_id` / `.user_id` and raise
   `PluginAbortError` to reject unauthorized requests.
3. **Filter at query time** — analytics endpoints accept optional
   `org_id` / `tenant_id` query params for per-tenant views.

This avoids invasive schema changes while still enabling per-tenant
governance.

### Future: Full Isolation (Design Notes)

For production multi-tenancy with data isolation, these changes would be
needed:

| Change | Impact |
|--------|--------|
| `tenant_id` column on `proxies`, `servers`, `tools` tables | Every entity scoped to a tenant |
| Storage layer `filter_by_tenant()` | All CRUD queries filter by `tenant_id` from context |
| Tenant context propagation | HTTP endpoints read from `X-Tenant-ID` header; MCP endpoints from `_meta.tenant_id` |
| Auth middleware | Validates tenant access before any operation |
| Separate DB schemas per tenant | Hard isolation at the database level |

The current `_meta` protocol is forward-compatible with all of these —
they are additive layers on top.

---

## 5. Cache Bypass for `on_before_list_tools`

### Problem

`server.py:229-242` serves cached tools **before** `engine.list_tools()` is
ever called, so `on_before_list_tools` does not fire on cache hits. An
authorization plugin that wants to block tool listing for a specific client
is completely bypassed.

### Fix

Move the `on_before_list_tools` call from `engine.py:77` to `server.py`,
before the cache check:

```python
# proxy/server.py — list_tools handler (revised flow)
# 1. Plugin: before_list_tools (called BEFORE cache)
ctx = PluginContext(slug=slug, method="list_tools", client_id=client_id)
try:
    await plugin_manager.execute_first("on_before_list_tools", ctx=ctx)
except PluginAbortError as e:
    send_error(-32001, str(e))
    return JSONResponse({"ok": True}, status_code=202)

# 2. Plugin: before_cache_lookup (existing)
plugin_cache = await plugin_manager.execute_first(
    "on_before_cache_lookup", slug=slug,
)

# 3. Cache check (existing) ...
```

The engine's `list_tools()` retains its own `on_before_list_tools` call for
the non-cached path (the `execute_first` already handles `None` return).

---

## 6. Response Modification Hook — `on_before_response_return`

### Problem

`on_after_tool_call` fires **after** `response_returned` event is logged.
A DLP / governance plugin that needs to redact or block the response has no
hook to do so.

### New Hook

```python
# plugin/base.py
async def on_before_response_return(self, ctx: PluginContext, result: dict) -> dict | None:
    """Called just before the response is returned to the client.

    Return a modified result dict, or None to pass through unchanged.
    Raise PluginAbortError to block the response entirely.
    """
```

### Execution Location

In `engine.py`, between the `server_response` and `response_returned` events:

```python
# proxy/engine.py — call_tool()
ctx["add_event"]("server_response", f"Response from server '{server['name']}'", {
    "result_summary": _truncate(result),
})

# Plugin: before_response_return
for plugin in plugin_manager.plugins:
    method = getattr(plugin, "on_before_response_return", None)
    if method is None:
        continue
    try:
        modified = await method(ctx=pctx, result=result)
        if modified is not None:
            result = modified
    except PluginAbortError as e:
        raise PermissionError(str(e)) from e

ctx["add_event"]("response_returned", ...)
```

---

## 7. Tool Filter Hook — `on_tool_filter`

### Problem

`on_after_list_tools` can observe the tool list but cannot modify it. A
governance plugin cannot hide sensitive tools from specific callers.

### New Hook

```python
# plugin/base.py
async def on_tool_filter(self, ctx: PluginContext, tools: list[dict]) -> list[dict]:
    """Filter the tool list before it is returned to the client.

    Return the (possibly modified) list of tools.
    """
```

### Execution Location

```python
# proxy/engine.py — list_tools()
# Plugin: after_list_tools
ctx = PluginContext(slug=slug, method="list_tools")
await plugin_manager.execute("on_after_list_tools", ctx=ctx, tools=tools)

# Plugin: tool_filter — each plugin gets a chance to filter
for plugin in plugin_manager.plugins:
    method = getattr(plugin, "on_tool_filter", None)
    if method is None:
        continue
    try:
        tools = await method(ctx=ctx, tools=tools)
    except PluginAbortError:
        raise  # plugin can abort listing entirely
    except Exception as e:
        log.error("Plugin %s tool_filter error: %s", plugin.name, e)

return tools
```

---

## 8. Standard Plugin API Route Contribution

### Problem

`MetricsPlugin` defines a `router` property but it is never mounted in the
running app (`app.py` has no reference to it). Plugins have no standard way
to expose HTTP endpoints.

### Solution

Add an optional `router` property to the `Plugin` base class:

```python
# plugin/base.py
from fastapi import APIRouter

class Plugin:
    ...
    @property
    def router(self) -> APIRouter | None:
        """Override to expose HTTP endpoints under /api/plugins/{name}/"""
        return None
```

Auto-mount in `app.py`:

```python
# api/app.py — after plugin registration
for plugin in plugin_manager.plugins:
    if plugin.router:
        app.include_router(plugin.router, prefix=f"/api/plugins/{plugin.name}")
```

---

## 9. Plugin Priority Ordering

### Problem

Plugins execute in registration order. A governance plugin that must run
before metrics (to reject before recording) cannot enforce ordering.

### Solution

```python
# plugin/base.py
class Plugin:
    ...
    priority: int = 0  # lower = runs first
```

In `PluginManager.execute()`:

```python
# Sort plugins by priority before execution
for plugin in sorted(self._plugins, key=lambda p: p.priority):
    ...
```

This is fully backward-compatible (default priority 0 for all existing
plugins).

### Recommended Priority Conventions

| Priority | Plugin Type | Example |
|----------|-------------|---------|
| -100 | Authentication | Validate API keys before anything |
| -50 | Authorization / Governance | ABAC, RBAC checks |
| 0 | Observability (default) | MetricsPlugin, audit logger |
| 50 | Rate Limiting | Check limits after auth |
| 100 | Cache | CachePlugin (latest possible) |

---

## 10. Complete File Change List

| # | File | Change |
|---|------|--------|
| **P1** | **PluginAbortError** | |
| 1 | `plugin/base.py` | Add `PluginAbortError` class |
| 2 | `plugin/manager.py` | `except PluginAbortError: raise` in `execute()` + `execute_first()` |
| 3 | `proxy/engine.py` | Wrap `on_before_tool_call` + `on_before_list_tools` — catch abort → `PermissionError` |
| 4 | `examples/plugins/rate_limiter.py` | `RuntimeError` → `PluginAbortError` |
| 5 | `examples/plugins/validation_plugin.py` | `ValueError`/`TypeError` → `PluginAbortError` |
| 6 | `tests/test_plugin.py` | Add abort tests |
| **P2** | **PluginContext identity + tenant fields** | |
| 7 | `plugin/base.py` | Add `client_id`, `user_id`, `org_id`, `tenant_id`, `meta` to `PluginContext` |
| **P3** | **Storage layer — all new fields** | |
| 8 | `registry/storage.py` | Add `span_id`, `parent_span_id`, `org_id`, `tenant_id`, `user_id` to abstract `record_call()` |
| 9 | `registry/json_storage.py` | Store all new fields in call dict |
| 10 | `registry/repository.py` | Pass all new fields to `ToolCall` model |
| 11 | `registry/models.py` | Add `span_id`, `parent_span_id`, `org_id`, `tenant_id`, `user_id` columns |
| 12 | `proxy/middleware.py` | Accept + auto-gen `span_id`; pass through all fields |
| 13 | `proxy/engine.py` | Extract all `_meta` fields → middleware + `PluginContext` |
| **P4** | **API + Graph changes** | |
| 14 | `api/routes/graph.py` | Build span tree from `parent_span_id` |
| 15 | `api/routes/analytics.py` | Add `org_id`, `tenant_id` query filters to `list_calls` |
| 16 | `api/schemas.py` | Add new fields to `CallRecordResponse`, `CallDetailResponse`, `TraceNode` |
| **P5** | **UI updates** | |
| 17 | `ui/src/api/client.ts` | Add `span_id`, `parent_span_id`, `org_id`, `tenant_id`, `user_id` to types |
| 18 | `ui/src/pages/Graph.tsx` | Render span parent-child hierarchy |
| 19 | `ui/src/pages/Analytics.tsx` | Show tenant context in trace modal |
| **P6** | **Docs and examples** | |
| 20 | `examples/client/python_client.py` | Add `_meta` session tracing example |
| 21 | `examples/plugins/governance_abac.py` | New — ABAC governance plugin example |
| 22 | `docs/plugin-hooks.md` | Document `PluginAbortError`, new hooks |
| 23 | `docs/plugin-architecture-v2.md` | This document |
| 24 | `README.md` | Document `_meta` protocol in Advanced Usage |
| **P7** | **Release** | |
| 25 | `__init__.py` + `pyproject.toml` | Bump to v3.2.0 |
| 26 | `tests/` | Full suite run |
| 27 | dist/ | Build + PyPI + GitHub |

**Total: 27 files across 7 phases.**

---

## 11. Implementation Order

| Phase | Focus | Files | Depends On |
|-------|-------|-------|------------|
| P1 | PluginAbortError | 6 files | Nothing |
| P2 | PluginContext fields | 1 file | P1 |
| P3 | Storage (span_id + tenant fields) | 6 files | P2 |
| P4 | API + Graph changes | 3 files | P3 |
| P5 | UI updates | 3 files | P4 |
| P6 | Docs + Examples | 5 files | P1-P5 |
| P7 | Release | 4 files | P1-P6 |

Phases are incremental and backward-compatible — each can be shipped
independently.
