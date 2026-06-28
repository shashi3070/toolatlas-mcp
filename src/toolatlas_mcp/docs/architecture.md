# Architecture Overview

## System Components

```
                    ┌──────────────────────────────────┐
                    │         FastAPI App               │
                    │  (api/app.py)                     │
                    │                                   │
                    │  ┌──────────┐  ┌────────────────┐ │
                    │  │ Web UI   │  │  REST API       │ │
                    │  │ (React)  │  │  /api/* routes  │ │
                    │  └──────────┘  └───────┬────────┘ │
                    └────────────────────────┼──────────┘
                                             │
                    ┌────────────────────────┼──────────┐
                    │                        │          │
                    ▼                        ▼          │
            ┌───────────────┐       ┌──────────────┐    │
            │  ProxyEngine   │       │  Registry    │    │
            │  (engine.py)   │       │  (routes)    │    │
            │                │       │              │    │
            │  list_tools()  │       │  CRUD ops    │    │
            │  call_tool()   │       └──────┬───────┘    │
            └───────┬───────┘               │            │
                    │                       │            │
                    └───────┬───────────────┘            │
                            │                            │
                            ▼                            │
                 ┌─────────────────────┐                 │
                 │   StorageBackend     │                 │
                 │  (repository.py)     │                 │
                 │                      │                 │
                 │  • JSONStorage       │                 │
                 │  • RegistryRepository │                 │
                 │    (SQLAlchemy)       │                 │
                 └─────────────────────┘                 │
                            │                            │
                            ▼                            │
                 ┌─────────────────────┐                 │
                 │   ConnectionManager  │                 │
                 │  (connection_mgr.py) │                 │
                 │                      │                 │
                 │  Shared MCPClient    │                 │
                 │  pool per server_id │                 │
                 └─────────────────────┘                 │
                            │                            │
                            ▼                            │
                 ┌─────────────────────┐                 │
                 │   Upstream MCP       │                 │
                 │   Servers            │                 │
                 │   (GitHub, Jira...)  │                 │
                 └─────────────────────┘                 │
                                                         │
                    ┌────────────────────────────────────┘
                    │
                    ▼
          ┌─────────────────────┐
          │   PluginManager      │
          │  (plugin/manager.py) │
          │                      │
          │  ┌──────────────────┐│
          │  │ CachePlugin      ││
          │  │ MetricsPlugin    ││
          │  │ CustomPlugin     ││
          │  └──────────────────┘│
          └─────────────────────┘
```

## Request Flows

### Tool Listing (`tools/list`)

```
MCP Client → proxy_message() → Plugin:on_before_cache_lookup → Engine:list_tools()
  → ConnectionManager → MCPClient.list_tools()
  → Plugin:on_after_list_tools → Plugin:on_after_cache_lookup → Response
```

### Tool Call (`tools/call`)

```
MCP Client → proxy_message() → Engine:call_tool()
  → Resolve tool→server → Get MCPClient
  → Storage:upsert_tool → Middleware:track()
  → Plugin:on_before_tool_call → MCPClient.call_tool()
  → Plugin:on_after_tool_call → Middleware:record_call() → Response
```

### Registry Sync (background, every 30s)

```
RegistrySyncService → ConnectionManager → MCPClient.list_tools()
  → Hash comparison → Upsert/Delete tools
  → Invalidate proxy caches
  → Plugin:on_tool_{added,updated,removed}
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Shared MCPClient pool | One TCP connection per server, reused across all proxies |
| Display name mapping | `_tool_to_server` maps client-visible names to server IDs; collision detection via `(ServerName)` suffix |
| Plugin error isolation | A plugin crash never propagates — logged and skipped |
| Three storage backends | JSON for dev/quickstart, SQLite for single-user, PostgreSQL for production |
| SHA-256 tool hashing | Efficient change detection without comparing full tool definitions |
| Background sync | Tools auto-discover without manual intervention |
| Per-proxy tool settings | Aliases, enabled/disabled, custom descriptions are proxy-scoped, not global |
