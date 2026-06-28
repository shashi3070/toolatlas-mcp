# ToolAtlas MCP Registry System

## 1. What Is the Registry?

The Registry is the **data layer** of ToolAtlas. It stores everything: servers, tools,
proxies, glossary terms, domains, and call records. Every API route, background sync,
and proxy engine operation reads from or writes to the registry.

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        API Routes                                 │
│  /api/servers  /api/tools  /api/proxies  /api/glossary ...        │
└─────────────────────┬────────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│                      StorageBackend (abstract)                     │
│  storage.py — 40+ async methods (create/list/get/update/delete)   │
└─────────────────────┬────────────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
┌──────────────────┐   ┌──────────────────────┐
│   JSONStorage     │   │ RegistryRepository    │
│  (json_storage.py)│   │   (repository.py)     │
│                   │   │                       │
│  Single JSON file │   │  SQLAlchemy ORM       │
│  /data.json       │   │  SQLite / PostgreSQL  │
└──────────────────┘   └──────────────────────┘
```

### Core Files

| File | Role |
|------|------|
| `registry/storage.py` | Abstract `StorageBackend` interface (40+ methods) |
| `registry/models.py` | SQLAlchemy ORM models (Server, Tool, Proxy, etc.) |
| `registry/repository.py` | `RegistryRepository` — SQLAlchemy implementation |
| `registry/json_storage.py` | `JSONStorage` — single-file JSON implementation |
| `registry/mcp_client.py` | `MCPClient` — connects to external MCP servers |
| `services/registry_sync.py` | `RegistrySyncService` — background tool sync |
| `db.py` | Database engine, session factory, storage factory |
| `config.py` | Settings that control storage type |

## 3. The `StorageBackend` Interface

Every data operation goes through this abstract class (`registry/storage.py`). It
defines the contract that both `JSONStorage` and `RegistryRepository` must fulfill.

```python
# registry/storage.py (key methods — 40+ total)
class StorageBackend:
    # ── Servers ────────────────────────────────────────
    async def create_server(self, name, transport, command, url): ...
    async def list_servers(self): ...
    async def get_server(self, server_id): ...
    async def update_server(self, server_id, **kwargs): ...
    async def update_server_status(self, server_id, connection_status, ...): ...
    async def delete_server(self, server_id): ...
    async def get_server_tool_count(self, server_id): ...

    # ── Tools ──────────────────────────────────────────
    async def upsert_tool(self, server_id, name, description, input_schema): ...
    async def list_tools(self, server_id=None): ...
    async def get_tool(self, tool_id): ...
    async def update_tool(self, tool_id, **kwargs): ...
    async def delete_tool(self, tool_id): ...

    # ── Proxies ────────────────────────────────────────
    async def create_proxy(self, name, slug, description): ...
    async def list_proxies(self): ...
    async def get_proxy(self, proxy_id): ...
    async def get_proxy_by_slug(self, slug): ...
    async def update_proxy(self, proxy_id, **kwargs): ...
    async def delete_proxy(self, proxy_id): ...
    async def link_server_to_proxy(self, proxy_id, server_id, selected_tools): ...
    async def unlink_server_from_proxy(self, proxy_id, server_id): ...
    async def get_proxy_servers(self, proxy_id): ...
    async def get_tool_setting(self, proxy_id, tool_id): ...
    async def upsert_tool_setting(self, proxy_id, tool_id, enabled, ...): ...

    # ── Glossary & Domains ─────────────────────────────
    async def create_domain(self, name, description): ...
    async def list_domains(self): ...
    async def create_glossary_term(self, domain_id, term, definition): ...
    async def list_glossary_terms(self): ...
    async def bulk_import_glossary(self, data): ...

    # ── Tool Calls (analytics) ─────────────────────────
    async def record_call(self, tool_name, proxy_id=None, ...): ...
    async def get_call(self, call_id): ...
    async def list_calls(self, ...): ...
    async def get_call_stats(self): ...
    async def get_proxy_stats(self, proxy_id): ...

    # ── Lifecycle ──────────────────────────────────────
    async def close(self): ...
    async def commit(self): ...
```

Every method is `async`. Both implementations (`JSONStorage` and `RegistryRepository`)
provide the same methods with identical signatures. The rest of the application never
needs to know which backend is active.

## 4. Data Models

All models are defined in `registry/models.py` as SQLAlchemy ORM classes. `JSONStorage`
replicates the same fields using plain Python dicts.

```
┌─────────────┐       ┌──────────────┐       ┌─────────────────┐
│   Server     │       │    Tool      │       │    Proxy         │
├─────────────┤       ├──────────────┤       ├─────────────────┤
│ id (PK)     │──┐    │ id (PK)      │       │ id (PK)         │
│ name        │  │    │ server_id(FK)│◄──────│ name            │
│ transport   │  │    │ name         │       │ slug (unique)   │
│ command     │  │    │ description  │       │ description     │
│ url         │  │    │ input_schema │       │ created_at      │
│ enabled     │  │    │ enabled      │       │ updated_at      │
│ connection_ │  │    │ tags (JSON)  │       └────────┬────────┘
│  status     │  │    │ domain (JSON)│            │
│ tool_hash   │  │    │ glossary_    │            │
│ last_tool_  │  │    │  term_ids    │            │
│  sync       │  │    └──────────────┘            │
└─────────────┘  │          │                     │
                 │          │  ┌──────────────────┘
                 │          │  │
                 │          ▼  ▼
                 │  ┌─────────────────┐
                 │  │ ProxyServer     │  (many-to-many link)
                 │  ├─────────────────┤
                 │  │ proxy_id (FK)   │
                 └──│ server_id (FK)  │
                    │ selected_tools  │
                    └─────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ ProxyToolSetting│    │   GlossaryTerm   │    │    Domain        │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ id (PK)         │    │ id (PK)         │    │ id (PK)         │
│ proxy_id (FK)   │    │ domain_id (FK)──┼───►│ name (unique)   │
│ tool_id (FK)    │    │ term            │    │ description     │
│ enabled         │    │ definition      │    │ created_at      │
│ custom_desc     │    │ created_at      │    └─────────────────┘
│ alias           │    │ updated_at      │
└─────────────────┘    └─────────────────┘

┌─────────────────┐
│   ToolCall       │
├─────────────────┤
│ id (PK)         │
│ trace_id        │
│ proxy_id (FK)   │
│ tool_id (FK)    │
│ tool_name       │
│ request_args    │
│ response_summary│
│ duration_ms     │
│ success         │
│ error_message   │
│ timestamp       │
│ events (JSON)   │
└─────────────────┘
```

Key model relationships:
- `Server` 1:N `Tool` — each server has many tools (models.py:24)
- `Server` 1:N `ProxyServer` — many-to-many via link table (models.py:49)
- `Proxy` 1:N `ProxyServer` — many-to-many via link table (models.py:48)
- `Proxy` 1:N `ProxyToolSetting` — per-proxy tool overrides (models.py:57)
- `Domain` 1:N `GlossaryTerm` — terms grouped by domain (models.py:74)
- `Tool` 1:N `ToolCall` — call history (models.py:97)

## 5. Two Storage Backends

### JSONStorage (`registry/json_storage.py`)

Used when `TOOLATLAS_STORAGE_TYPE=json` (the default).

**How it works:**
- `JSONStorage:42-50` — On `load()`, reads the entire JSON file into memory
- `JSONStorage:51-55` — On `_save()`, serializes everything to disk
- All mutations acquire `asyncio.Lock()` at `json_storage.py:44` to prevent
  concurrent write corruption

**Performance characteristic:** Simple, no external dependencies. The entire dataset
must fit in memory. Good for single-node development or small deployments.

```python
# api/app.py:82-87
if app_settings.storage_type == "json":
    from toolatlas_mcp.registry.json_storage import JSONStorage
    s = JSONStorage(get_data_dir() / "data.json")
    await s.load()
    return s
```

The data file lives at:
- Windows: `%APPDATA%/ToolAtlas/data.json`
- Linux/macOS: `~/.toolatlas/data.json`
- Override via `TOOLATLAS_DATA_DIR` env var (`storage.py:11-14`)

### RegistryRepository (`registry/repository.py`)

Used when `TOOLATLAS_STORAGE_TYPE=db` (SQLite/PostgreSQL).

**How it works:**
- Uses SQLAlchemy async ORM with an `AsyncSession` passed in constructor
- `RegistryRepository:13` — `_model_to_dict()` converts ORM objects to plain dicts
- `RegistryRepository:30-34` — `commit()` handles rollback on error
- Each background service gets its **own session** to avoid `"concurrent operations
  are not permitted"` errors

```python
# api/app.py:89-93
from toolatlas_mcp.registry.repository import RegistryRepository
factory = _get_session_factory()
session = factory()
return RegistryRepository(session)
```

### How the Backend Is Selected

```python
# config.py
class Settings(BaseSettings):
    storage_type: str = "json"       # "json" or "db"
    database_url: str = f"sqlite+aiosqlite:///{get_data_dir() / 'toolatlas.db'}"
```

When `storage_type` is `"json"`, `JSONStorage` is used. When `"db"`, SQLAlchemy
connects to the `database_url` (SQLite or PostgreSQL). The `get_storage()` dependency
in `db.py:71-88` handles the selection:

```python
# db.py:71-88
async def get_storage() -> StorageBackend:
    if settings.storage_type == "json":
        storage = JSONStorage(json_path)
        await storage.load()
        yield storage
        await storage.save()
        await storage.close()
    else:
        factory = _get_session_factory()
        async with factory() as session:
            yield RegistryRepository(session)
```

API routes depend on `get_storage()` via FastAPI's `Depends`:

```python
# api/routes/tools.py:16
@router.get("")
async def list_tools(storage: StorageBackend = Depends(get_storage)):
    tools = await storage.list_tools(server_id=server_id)
```

## 6. MCPClient — Talking to External Servers

The `MCPClient` (`registry/mcp_client.py`) is how ToolAtlas communicates with
upstream MCP servers. It implements the **JSON-RPC 2.0** protocol over three
transport types:

| Transport | Connect Method | How It Works |
|-----------|---------------|--------------|
| `sse` | `_connect_sse()` | Opens an SSE stream, waits for `endpoint` event, then sends POST to message URL |
| `streamable-http` | `_connect_streamable_http()` | Opens SSE stream + POST with `mcp-session-id` header |
| `stdio` | `_connect_stdio()` | Spawns a subprocess, communicates via stdin/stdout |

```python
# registry/mcp_client.py:236-256
async def list_tools(self) -> list[dict]:
    resp = await self.send_request("tools/list")
    return resp["result"].get("tools", [])

async def call_tool(self, name: str, arguments: dict) -> dict:
    resp = await self.send_request("tools/call", {"name": name, "arguments": arguments})
    return resp["result"]

async def initialize(self):
    resp = await self.send_request("initialize", {
        "protocolVersion": "2024-11-05",
        "clientInfo": {"name": "toolatlas-mcp", "version": "0.1.0"},
    })
    await self.send_request("notifications/initialized")
```

**The pending-request pattern:**
- `MCPClient:20` — `_pending: dict[str, asyncio.Future]` maps message IDs to futures
- `MCPClient:156-159` — When sending a request, creates a future and stores it
- `MCPClient:69-71` — Incoming SSE messages wake the correct future by ID
- `MCPClient:178-181` — 30-second timeout on all requests

## 7. RegistrySyncService — Background Tool Sync

The `RegistrySyncService` (`services/registry_sync.py`) runs every 30 seconds
and keeps ToolAtlas in sync with upstream MCP servers.

### Sync Flow

```python
# registry_sync.py:61-73
async def _sync_loop(self, storage, cm):
    while True:
        servers = await storage.list_servers()
        for server in servers:
            if not server.get("enabled"):
                continue
            await self._sync_server(storage, cm, server)
        await asyncio.sleep(30)
```

### Per-Server Sync (`_sync_server`, line 75-162)

```python
# registry_sync.py:75-162 (simplified)
async def _sync_server(self, storage, cm, server):
    # 1. Get or create shared connection via ConnectionManager
    client = await cm.get_client(server)

    # 2. Fetch current tool list from server
    remote_tools = await client.list_tools()

    # 3. Hash comparison to detect changes
    new_hash = _compute_tool_hash(remote_tools)
    if new_hash == current_hash:
        return  # No changes, skip

    # 4. Upsert each tool (create or update)
    for rt in remote_tools:
        await storage.upsert_tool(server_id, name, description, input_schema)

    # 5. Delete tools no longer on the server
    for name in existing_names - remote_names:
        await storage.delete_tool(existing[name]["id"])

    # 6. Update server's tool_hash and last_tool_sync
    await storage.update_server(server["id"], tool_hash=new_hash, ...)

    # 7. Invalidate affected proxy caches
    await invalidate_proxies_for_server(server["id"], storage)

    # 8. Notify plugins
    await plugin_manager.execute("on_tool_added", ...)
    await plugin_manager.execute("on_tool_updated", ...)
    await plugin_manager.execute("on_tool_removed", ...)
```

### Hash-Based Change Detection

```python
# registry_sync.py:17-21
def _compute_tool_hash(remote_tools: list[dict]) -> str:
    sorted_tools = sorted(remote_tools, key=lambda t: t.get("name", ""))
    raw = json.dumps(sorted_tools, sort_keys=True)
    return hashlib.sha256(raw).hexdigest()
```

This SHA-256 hash is stored in `Server.tool_hash` (`models.py:35`). If the hash
hasn't changed, the entire sync is skipped — no database writes, no cache
invalidation, no plugin notifications. This makes the common case (no changes)
extremely cheap.

### How It Connects

The sync uses `ConnectionManager` to get shared MCP client connections:

```python
# services/connection_manager.py
class ConnectionManager:
    async def get_client(self, server: dict) -> MCPClient:
        # Returns existing connection or creates a new one
        # Connections are shared across sync + proxy engine
```

This avoids creating a new MCP session for every sync cycle.

### Sync Startup

In `api/app.py:111-114`:

```python
from toolatlas_mcp.services.registry_sync import RegistrySyncService
_registry_task = asyncio.create_task(
    RegistrySyncService()._sync_loop(sync_storage, connection_manager)
)
```

Each background service gets its own storage instance (`sync_storage`) with its
own DB session to avoid concurrent-operation errors.

## 8. Data Flow: End-to-End Examples

### Example 1: Creating a Server

```
POST /api/servers {"name": "GitHub", "transport": "sse", "url": "http://..."}
  │
  ▼
api/routes/servers.py → create_server(storage=Depends(get_storage))
  │
  ▼
storage.create_server("GitHub", "sse", url="http://...")
  │
  ├─ JSON: appends to _data["servers"], saves file
  └─ DB:   INSERT INTO servers (id, name, transport, url, ...)
  │
  ▼
Returns ServerResponse to client

Background (async):
  ▼
RegistrySyncService._sync_loop notices the new server
  ├─ cm.get_client(server) → MCPClient connected via SSE
  ├─ client.list_tools() → ["search_issues", "get_repo", ...]
  ├─ storage.upsert_tool() for each tool
  ├─ storage.update_server(tool_hash=..., connection_status="connected")
  └─ plugin_manager.execute("on_tool_added", ...)
```

### Example 2: Listing Tools via a Proxy (MCP Client)

```
MCP Client → POST /proxy/dev/message/{session_id} (JSON-RPC: tools/list)
  │
  ▼
proxy/server.py:215-245 → proxy_message(slug="dev")
  │
  ├─ plugin_manager.execute_first("on_before_cache_lookup", slug="dev")
  │   → CachePlugin checks memory → Redis
  │
  ├─ Check in-process cache (_tools_cache with 60s TTL + jitter)
  │
  ├─ If miss: engine.list_tools("dev")
  │   │
  │   ▼
  │   proxy/engine.py:list_tools(slug)
  │     │
  │     ├─ storage.get_proxy_by_slug("dev")
  │     ├─ storage.get_proxy_servers(proxy_id)
  │     ├─ For each server: get linked + enabled tools
  │     │   storage.get_tool_setting(proxy_id, tool_id)
  │     │   storage.get_glossary_term(term_id)  # for enrichment
  │     │
  │     ├─ Apply aliases, custom descriptions, enrichment
  │     │
  │     └─ plugin_manager.execute("on_after_list_tools", ctx, tools)
  │
  ├─ plugin_manager.execute("on_after_cache_lookup", slug, tools)
  │
  └─ Send {"tools": [...]} to MCP client via SSE
```

### Example 3: Calling a Tool via a Proxy

```
MCP Client → POST /proxy/dev/message/{session_id} (JSON-RPC: tools/call)
  │
  ▼
proxy/server.py:247-254 → engine.call_tool("dev", "search_issues", {jql: "..."})
  │
  ▼
proxy/engine.py:call_tool(slug, name, arguments)
  │
  ├─ Build PluginContext(slug="dev", tool_name="search_issues", ...)
  │
  ├─ plugin_manager.execute("on_before_tool_call", ctx=pctx)
  │   → MetricsPlugin injects start_time
  │   → **Raise here to block the call**
  │
  ├─ Check permissions via ProxyToolSetting.enabled
  │
  ├─ Forward to MCP server via shared ConnectionManager
  │   client.call_tool("search_issues", {jql: "..."})
  │   └─ Returns result from upstream server
  │
  ├─ Record call in storage.record_call(...)
  │
  ├─ Compute duration, inject into ctx.extra
  │
  └─ plugin_manager.execute("on_after_tool_call", ctx=pctx, result=result)
      → MetricsPlugin increments count, records duration
  │
  ▼
Send result to MCP client via SSE
```

## 9. Schema Migrations

Database schema migrations are handled in `db.py:110-125`:

```python
async def _migrate_schema(conn, dialect: str):
    existing_columns = await _get_existing_columns(conn, dialect)
    migrations = [
        ("servers", "tool_hash", "VARCHAR"),
        ("servers", "last_tool_sync", "DATETIME"),
        ("tool_calls", "events", "JSON"),
    ]
    for table, col, coltype in migrations:
        if col not in existing_columns.get(table, set()):
            await conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {ct[coltype]};")
```

Runs at startup in `init_db()` after `Base.metadata.create_all`. New columns are
added via `ALTER TABLE` only if they don't already exist.

## 10. Storage Independence Summary

The `StorageBackend` abstraction means:
- API routes never import `JSONStorage` or `RegistryRepository` directly — they
  depend on `StorageBackend` via `Depends(get_storage)`
- The proxy engine and background services receive a `StorageBackend` instance
  at construction time
- Switching from JSON to DB storage is a single config change:
  `TOOLATLAS_STORAGE_TYPE=db`

```python
# api/app.py:81-93
async def _create_storage():
    if app_settings.storage_type == "json":
        from toolatlas_mcp.registry.json_storage import JSONStorage
        s = JSONStorage(get_data_dir() / "data.json")
        await s.load()
        return s
    else:
        from toolatlas_mcp.registry.repository import RegistryRepository
        session = factory()
        return RegistryRepository(session)
```
