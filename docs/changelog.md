# Changelog

## v3.0.0

| Area | Change | Impact |
|------|--------|--------|
| **ConnectionManager** | Shared `MCPClient` pool — one client per `server_id` reused across all proxies | Eliminates redundant connections; auto-reconnects stale clients; reduces total TCP connections |
| **Background Registry Sync** | Periodic SHA-256 sync of all upstream servers (default 30s) | Tools auto-discover, update, and remove without manual `discover`; stale detection is continuous |
| **Plugin Architecture** | Hook-based plugin system with `on_before_tool_call`, `on_after_tool_call`, `on_before_cache_lookup`, `on_tool_added`/`updated`/`removed` | Extend ToolAtlas without modifying core — built-in Cache + Metrics plugins included |
| **Cache Plugin (built-in)** | Memory→Redis two-tier cache with TTL jitter, warmup on startup, and stats | Redis as optional shared cache layer (`TOOLATLAS_REDIS_URL`); falls back to memory if unavailable |
| **Metrics Plugin (built-in)** | Prometheus-compatible counters for call count, latency, errors, cache hit ratio | `/metrics` endpoint for Prometheus scraping; no external dependencies beyond `prometheus-client` |
| **TTL Jitter** | Cache TTL randomly jittered by ±10% | Prevents thundering herd when multiple proxy TTLs expire simultaneously |
| **Tool Name Collision Detection** | ProxyEngine detects same-named tools from different servers and appends `(ServerName)` suffix | Each tool remains addressable by a unique name |
| **Alias System** | Per-proxy tool aliases with inline editing in the UI | Rename tools without modifying upstream servers; original name always preserved |

## v2.0.0

| Area | Change | Impact |
|------|--------|--------|
| **PostgreSQL** | Dialect-aware `connect_args`, `AsyncAdaptedQueuePool` (pool=10, overflow=20), early `asyncpg` import check | PostgreSQL now works reliably without crashes or per-query TCP overhead |
| **Transaction safety** | `commit()` wraps exceptions with `rollback()` — poisoned sessions are cleaned up | Eliminates `ResourceClosedError: This transaction is closed` errors |
| **Cache locking** | `list_tools` cache miss uses double-checked locking under `_engine_locks[slug]` | Prevents redundant `list_tools` flood when multiple domains' TTLs expire simultaneously |
| **Batch commits** | Proxy link-server tool disabling now uses `auto_commit=False` + single `commit()` | 130 toggles → 1 commit instead of 130 |
| **Stale detection** | Tool cache cleared immediately when any upstream client goes stale (not only when all are gone) | No stale tools returned after partial connection loss |
| **Import hygiene** | `from sqlalchemy import JSON` instead of `sqlalchemy.dialects.sqlite.JSON` | Cleaner, semantically correct for all dialects |

## v1.0.0

Initial release:
- MCP proxy server with SSE transport
- Tool registry with SQLite/JSON/PostgreSQL storage
- Proxy groups for tool governance
- Tool enrichment (tags, domains, glossary terms)
- Analytics and call tracking
- Web dashboard UI
- Tool testing console
- Glossary management
- Search across tools, servers, glossary
- Tool Graph visualization
