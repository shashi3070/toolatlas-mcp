# ToolAtlas

**The Knowledge Layer for MCP Tools**

[![PyPI version](https://img.shields.io/pypi/v/toolatlas-mcp)](https://pypi.org/project/toolatlas-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/toolatlas-mcp)](https://pypi.org/project/toolatlas-mcp/)
[![License](https://img.shields.io/pypi/l/toolatlas-mcp)](LICENSE)

![Architecture](https://raw.githubusercontent.com/shashi3070/toolatlas-mcp/main/screenshots/toolatlas-architecture.png)

ToolAtlas helps organizations **discover, govern, understand, and optimize** MCP tools without modifying existing MCP servers.

```bash
pip install toolatlas-mcp
toolatlas start                  # defaults: port 8081, json storage
toolatlas start --port 9000 --storage sqlite --data-dir ./data
toolatlas start --storage postgres --database-url "postgresql+asyncpg://user:pass@localhost:5432/toolatlas"
```

---

## Documentation

Full documentation is in the [`docs/`](https://github.com/shashi3070/toolatlas-mcp/tree/main/docs) directory.

| Area | Documents |
|------|-----------|
| **Plugin System** | [plugin-system.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/plugin-system.md), [plugin-loading.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/plugin-loading.md), [plugin-hooks.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/plugin-hooks.md), [plugin-examples.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/plugin-examples.md), [plugin-testing.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/plugin-testing.md) |
| **Core System** | [proxy-engine.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/proxy-engine.md), [tool-graph.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/tool-graph.md), [registry.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/registry.md), [architecture.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/architecture.md) |
| **API & CLI** | [api.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/api.md), [cli.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/cli.md), [configuration.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/configuration.md) |
| **Operations** | [deploy-under-subpath.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/deploy-under-subpath.md), [troubleshooting.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/troubleshooting.md) |
| **Development** | [development.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/development.md), [changelog.md](https://github.com/shashi3070/toolatlas-mcp/blob/main/docs/changelog.md) |
| **Examples** | [examples/](https://github.com/shashi3070/toolatlas-mcp/tree/main/examples) — runnable Python scripts |

> **Tip:** Run `toolatlas docs` from the CLI to find your local copy of the docs (shipped with the installed package).

---

## Why ToolAtlas?

As MCP adoption grows, teams quickly accumulate hundreds of tools across GitHub, Jira, Confluence, AWS, Databricks, Slack, internal systems, and custom MCP servers. **The challenge is no longer connecting tools — it's understanding them.**

| Problem | How ToolAtlas Solves It |
|---------|------------------------|
| **Tool Sprawl** | Central catalog of every MCP tool — see what exists, what's used, what's duplicated, what's dangerous |
| **Lack of Business Context** | Add business descriptions, aliases, tags, domain categories, and glossary definitions — without modifying the original server |
| **Governance** | Per-proxy enable/disable, tool selection on server link, audit logging via call traces |
| **Tool Intelligence** | Usage analytics, success rates, latency tracking, top tools by usage |

ToolAtlas sits between AI clients and MCP servers — it's the **control plane** for your MCP ecosystem.

> "LiteLLM manages models. **ToolAtlas manages tools.** "

---

## Key Features

### 📋 MCP Tool Catalog
Central inventory of all MCP tools across all your servers — searchable, filterable, sortable from the web dashboard.

![Dashboard](https://raw.githubusercontent.com/shashi3070/toolatlas-mcp/main/screenshots/dashboard.png)

### 🗂️ Proxy Groups — Organize Tools by Team or Purpose
Create proxies (named groups) and assign MCP servers to each. Every proxy exposes a different toolset.

```
Proxy "dev"    → GitHub + GitLab     (for developers)
Proxy "pm"     → Jira + Confluence   (for project managers)
Proxy "devops" → AWS + PagerDuty     (for operations)
```

![Proxy Configuration](https://raw.githubusercontent.com/shashi3070/toolatlas-mcp/main/screenshots/proxy.png)

### 🛡️ Per-Tool Governance — Control What Each Proxy Exposes
Every tool can be independently configured **per proxy**:

| Control | What it does |
|---------|-------------|
| **Enable / Disable** | Block dangerous tools (e.g. `delete_repo`) without touching the server |
| **Custom Description** | Rewrite the tool's description so AI agents understand it in context |
| **Alias** | Rename the tool per proxy |
| **Tool Selection on Link** | Pick exactly which tools to expose when linking a server — unselected tools auto-disable |

![Tool Detail & Enrichment](https://raw.githubusercontent.com/shashi3070/toolatlas-mcp/main/screenshots/tool1.png)

### 🏷️ Tool Enrichment — Make Tools Smarter
Every registry tool can be enriched with business context. The enriched description is what clients see when they call `list_tools`:

| Enrichment | Purpose | Example in client view |
|---|---|---|
| **Custom Description** | Override the original server description | `Search for code in GitHub` |
| **Tags** | Add searchable labels | `Tags: git, code, search` |
| **Domain** | Categorize by business area | `Domain: development` |
| **Glossary Terms** | Link one or more business concepts with definitions | `Glossary: Search across all code repositories` |

Client sees the full enriched description automatically:

```json
{
  "name": "search_code",
  "description": "Search code in GitHub repositories\nTags: git, code\nDomain: development\nGlossary: Search code across all repositories",
  "inputSchema": { ... }
}
```

### 📊 Usage Analytics
Every tool call is tracked — duration, success/failure, arguments. Dashboard shows top tools, latency trends, error rates, and per-call trace timelines.

![Analytics](https://raw.githubusercontent.com/shashi3070/toolatlas-mcp/main/screenshots/analytics%20page.png)

### 🌐 Web Dashboard
Full SPA for managing everything visually — servers, proxies, tool settings, glossary, analytics.

### 🧪 Tool Testing Console
Test any tool directly from the UI — pass arguments via a dynamic form (auto-generated from the tool's input schema) and see the result in real time with duration tracking.

### 📂 Glossary with Domain Hierarchy
Organize glossary terms under domains (created first, then terms under them). Terms are grouped by domain in the UI. Assign **multiple** glossary terms to a single tool. Edit/delete domains and terms inline. Bulk import entire glossaries via JSON/CSV file upload with automatic domain creation.

### 🔍 Filters & Search
Every management page (Tools, Servers, Proxies, Glossary, Analytics) includes search bars and filter dropdowns for quick navigation.

### 🕸️ Tool Graph — Visualize Relationships & Execution Workflows
Explore how your MCP ecosystem connects. The Graph page offers three views:

- **Call Flow** — See the ordered sequence of tool calls within a single execution trace. Each call is a node; arrows show the execution order with timing labels. Click any trace in the side panel to visualize its flow as a directed acyclic graph.
- **Relationships** — Discover which tools are frequently called together. A force-directed graph shows co-occurrence strength via edge thickness and node size (call count). The side panel lists tool pairs ranked by co-occurrence count.
- **Topology** — The full infrastructure graph: proxies, servers, and their tools. Proxy-to-server edges are dashed; server-to-tool edges are solid. Color-coded by type (blue=proxy, green=server, amber=tool).

**API endpoints:**
| Endpoint | Returns |
|----------|---------|
| `GET /api/graph` | Full topology (proxies, servers, tools) |
| `GET /api/graph/proxy/{id}` | Topology scoped to a single proxy |
| `GET /api/graph/traces` | Recent execution traces with tool counts, duration, success rate |
| `GET /api/graph/trace/{id}` | Ordered call flow DAG for a specific trace |
| `GET /api/graph/co-occurrence` | Tool co-occurrence pairs with weights, filterable by proxy |

### 🔮 Planned Features
| Feature | Status |
|---------|--------|
| **Tool Recommendations** — Recommend the best tools for tasks based on usage patterns | Planned |

---

## Architecture

```
┌─────────────────┐     ┌─────────────────────────────────────┐     ┌─────────────────┐
│  MCP Clients    │     │         ToolAtlas                    │     │  MCP Servers     │
│                 │     │                                     │     │                  │
│  Claude         │────▶│  Proxy "dev"     ── governance ──▶ │────▶│  GitHub MCP      │
│  Cursor         │────▶│  Proxy "pm"      ── governance ──▶ │────▶│  Jira MCP        │
│  Custom Agents  │────▶│  Proxy "devops"  ── governance ──▶ │────▶│  Slack MCP       │
│                 │     │                                     │     │  Confluence MCP  │
│                 │     │  ┌──────────────┐  ┌─────────────┐ │     │  AWS MCP         │
│                 │     │  │ Registry     │  │ Analytics   │ │     │  Custom MCP      │
│                 │     │  │ DB + API     │  │ Tracker     │ │     └─────────────────┘
│                 │     │  └──────────────┘  └─────────────┘ │
│                 │     │  ┌──────────────────────────────┐  │
│                 │     │  │  Web Dashboard (React SPA)   │  │
│                 │     │  └──────────────────────────────┘  │
│                 │     │  ┌──────────────────────────────┐  │
│                 │     │  │  CLI: toolatlas start/add    │  │
│                 │     │  └──────────────────────────────┘  │
│                 │     └─────────────────────────────────────┘
```

Clients speak MCP to ToolAtlas. ToolAtlas enforces governance, enriches tool descriptions, logs every call, and forwards to real MCP servers.

---

## Installation

### Prerequisites

- **Python 3.10+** ([download](https://python.org/downloads))
- **pip** (comes with Python)

### Install from PyPI (recommended)

```bash
pip install toolatlas-mcp
```

**PostgreSQL support** (optional — requires `asyncpg`):

```bash
pip install "toolatlas-mcp[postgres]"
```

Verify it installed:

```bash
toolatlas --help
```

You should see the CLI help with `start`, `server`, `proxy` commands.

### Install from source

```bash
git clone https://github.com/shashi3070/toolatlas-mcp
cd toolatlas-mcp

# Python package
pip install -e ".[dev]"

# Build the web UI
cd ui
npm install
npm run build
cd ..
```

---

## Usage — Step by Step

### 1. Start the Server

```bash
toolatlas start
```

Output:
```
ToolAtlas starting on 127.0.0.1:8081
  Web UI: http://127.0.0.1:8081
  API:    http://127.0.0.1:8081/api/health
```

Open **http://localhost:8081** in your browser to see the dashboard.

### 2. Add an MCP Server

![Server Management](https://raw.githubusercontent.com/shashi3070/toolatlas-mcp/main/screenshots/server.png)

You can add servers via CLI or the web UI.

**CLI — stdio server (e.g., npx-based):**

```bash
toolatlas server add github \
  --transport stdio \
  --command "npx" \
  --args "-y" "@modelcontextprotocol/server-github"
```

**CLI — SSE server (already running):**

```bash
toolatlas server add my-api \
  --transport sse \
  --url "http://localhost:9001/sse"
```

**Web UI:** Go to **Servers** → **Add Server**, fill in the details.

### 3. Discover Tools

After adding a server, discover its tools:

```bash
# Via CLI (uses the API):
curl -X POST http://localhost:8080/api/servers/{server_id}/discover
```

Or click **Discover & Save New** on the Server detail page in the web UI.

### 4. Create a Proxy

Proxies organize tools into groups. Each proxy exposes a subset of your servers' tools.

```bash
# Create a proxy
toolatlas proxy add dev --description "Developer tools"

# Link servers to it
toolatlas proxy link dev github
toolatlas proxy link dev gitlab
```

List your proxies:

```bash
toolatlas proxy list
```

> **Tip:** In the web UI, when linking a server you can **select exactly which tools** to expose — unselected tools are automatically disabled for that proxy. No need to manually toggle them afterwards.

### 5. Configure Tools Per Proxy

In the web UI, go to a **Proxy detail page** → **Tools** tab. For each tool:

- **Toggle enabled/disabled** — disable `delete_repo` for the "dev" proxy
- **Set a custom description** — e.g., "Search code in GitHub repos"
- **Alias the tool** — rename it for clarity

You can also select which tools to include at link time — click **Link** next to a server to open the tool picker modal.

### 6. Enrich Tool Metadata

![Tool Enrichment Settings](https://raw.githubusercontent.com/shashi3070/toolatlas-mcp/main/screenshots/tool%20update%20screen.png)

In the **Tool detail page**, you can add:

- **Tags** — comma-separated labels like `git, code, search`
- **Domain** — categorize the tool (e.g., "development", "security")
- **Glossary Terms** — link one or more business terms with definitions (multi-select, grouped by domain)

First create glossary **domains** and **terms** under the **Glossary** page, then assign them to tools from the tool detail page.

### 7. Connect Your AI Client

Configure your MCP client (Claude Desktop, Cursor, custom agent) to point to ToolAtlas. Replace `dev` with your proxy's slug name.

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "dev": {
      "type": "sse",
      "url": "http://localhost:8081/proxy/dev/sse"
    }
  }
}
```

**Cursor / VS Code / any MCP client** — same format; just register an SSE server with the URL above.

The proxy slug (`dev`, `prod`, etc.) is the name you gave when creating the proxy. Each proxy exposes a different toolset.

#### Advanced: Raw JSON-RPC (without SSE)

For scripting or testing without an MCP client library, use the message endpoint directly. Each call needs its own `session_id` (UUID).

```python
import httpx, uuid

session_id = str(uuid.uuid4())
proxy_url = f"http://localhost:8081/proxy/dev/message/{session_id}"

# Initialize
httpx.post(proxy_url, json={
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}
}).json()

# Notify initialized
httpx.post(proxy_url, json={
    "jsonrpc": "2.0", "method": "notifications/initialized"
}).json()

# List tools
httpx.post(proxy_url, json={
    "jsonrpc": "2.0", "id": 2, "method": "list_tools"
}).json()

# Call a tool
httpx.post(proxy_url, json={
    "jsonrpc": "2.0", "id": 3, "method": "call_tool",
    "params": {"name": "search_code", "arguments": {"query": "auth"}}
}).json()
```

### 8. View Analytics

Go to the **Analytics** page in the web UI to see:
- Total calls, success rate, average latency
- Top tools by usage
- Individual call traces with event timelines (proxy resolution → server call → response)

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `toolatlas start` | Start the ToolAtlas server (defaults: port 8081, json storage) |
| `toolatlas start --port 9000 --host 0.0.0.0` | Start on a different address |
| `toolatlas start --storage sqlite` | Use SQLite storage backend |
| `toolatlas start --storage postgres --database-url "postgresql+asyncpg://user:pass@host:5432/db"` | Use PostgreSQL storage backend |
| `toolatlas start --database-url "postgresql+asyncpg://..."` | Set database URL directly (any SQLAlchemy dialect) |
| `toolatlas start --data-dir ./my-data` | Custom data directory |
| `toolatlas start --reload` | Start with auto-reload (development) |
| `toolatlas start --base-path /toolatlas` | Start with reverse proxy base path prefix |

All flags: `--port`, `--host`, `--storage` (json/sqlite/postgres), `--database-url`, `--data-dir`, `--base-path`, `--reload`. Environment variables are still supported with `TOOLATLAS_` prefix and take precedence over defaults. You can also use a `.env` file in the working directory to set any `TOOLATLAS_*` variable.

---

## Storage

ToolAtlas supports three storage backends:

| Backend | Type | Best for |
|---------|------|----------|
| **JSON File** (default) | `json` | Development, single-user, portable setups, git-versioned data |
| **SQLite** | `sqlite` | Production, multi-user, analytics-heavy workloads (good for up to ~10 concurrent connections) |
| **PostgreSQL** | `postgres` | Production, high-concurrency, many concurrent connections (no write-lock contention) |

### Storage Backend Comparison

| Feature | JSON | SQLite | PostgreSQL |
|---------|------|--------|------------|
| **Dependencies** | built-in | built-in | `pip install toolatlas-mcp[postgres]` |
| **Concurrent reads** | asyncio-lock serialized | WAL mode (reads don't block reads) | Full MVCC |
| **Concurrent writes** | asyncio-lock serialized | One writer at a time (WAL mode) | Many concurrent writers |
| **Persistence** | Single file | Single file | External server |
| **Setup** | None | None | Requires running PostgreSQL instance |

> **Tip:** SQLite with WAL mode + batch commits (v1.13+) handles moderate concurrency well. Switch to PostgreSQL when you have many concurrent proxy instances or tool discovery calls happening at the same time.

### PostgreSQL Connection Pooling (v2.0.0+)

When using PostgreSQL, ToolAtlas automatically configures:
- **`AsyncAdaptedQueuePool`** with `pool_size=10` and `max_overflow=20` — no new TCP connection per query
- **`command_timeout=10`** — proper asyncpg parameter (not the aiosqlite `timeout`)
- **Early `asyncpg` detection** — a clear `RuntimeError` is raised at import if `asyncpg` is missing

The `data.json` file is saved to the same data directory as the SQLite database.

---

## v3.0 Advanced Features

### 🔌 Plugin System

ToolAtlas v3.0 ships with a hook-based plugin architecture. Plugins can intercept and extend every major lifecycle event.

**Built-in plugins:**

| Plugin | Entry point | Enables via |
|--------|------------|-------------|
| Redis/Memory Cache | `cache` | `TOOLATLAS_PLUGINS=cache` |
| Prometheus Metrics | `metrics` | `TOOLATLAS_PLUGINS=metrics` |

**Available hooks (all optional):**

| Hook | Fires | Use case |
|------|-------|----------|
| `on_before_list_tools` | Before listing tools for a proxy | Modify or filter tool list |
| `on_after_list_tools` | After listing | Log results, inject extra tools |
| `on_before_tool_call` | Before executing a tool | Validate arguments, audit |
| `on_after_tool_call` | After tool execution | Record results, metrics |
| `on_before_cache_lookup` | Before cache read | Return cached data early |
| `on_after_cache_lookup` | After cache read | Track hit/miss stats |
| `on_cache_invalidated` | When cache is cleared | Propagate invalidation to Redis |
| `on_tool_added` | Registry sync discovers a new tool | Notify, index |
| `on_tool_updated` | Registry sync detects changes | Re-index |
| `on_tool_removed` | A tool is deleted from a server | Clean up |
| `on_server_connected` | A new MCP client connects | Tag connections |
| `on_startup` / `on_shutdown` | Server lifecycle | Initialize / teardown resources |

**Enable plugins:**

```bash
# Via environment variable
export TOOLATLAS_PLUGINS="cache,metrics"

# Or via CLI
toolatlas start
```

**Plugin discovery order:**
1. Entry points registered in `pyproject.toml` under `[project.entry-points."toolatlas.plugins"]`
2. Directories listed in `TOOLATLAS_PLUGIN_DIRS`
3. Module paths listed in `TOOLATLAS_PLUGINS`

**Write a custom plugin:**

```python
from toolatlas_mcp.plugin.base import Plugin, PluginContext

class MyPlugin(Plugin):
    name = "my_plugin"

    async def on_before_tool_call(self, ctx: PluginContext, tool_name: str, arguments: dict) -> None:
        print(f"Tool {tool_name} called with {arguments}")

    async def on_after_tool_call(self, ctx: PluginContext, tool_name: str, result: dict) -> None:
        print(f"Tool {tool_name} returned: {result}")
```

Register via entry point in `pyproject.toml`:
```toml
[project.entry-points."toolatlas.plugins"]
my_plugin = "my_package.plugins:MyPlugin"
```

### 🗄️ Redis Cache (built-in plugin)

When the `cache` plugin is enabled, ToolAtlas uses a two-tier cache:

1. **Memory** (in-process dict, shared across all proxies for the same server)
2. **Redis** (optional, when `TOOLATLAS_REDIS_URL` is set)

```bash
export TOOLATLAS_PLUGINS="cache"
export TOOLATLAS_REDIS_URL="redis://localhost:6379/0"
export TOOLATLAS_CACHE_TTL=300
```

Without Redis, the cache plugin operates in memory-only mode. If Redis is configured but unreachable, it falls back to memory automatically.

Cache keys are `tools:{slug}` with TTL equal to `TOOLATLAS_CACHE_TTL`. Each cache hit refreshes the TTL.

### 📊 Prometheus Metrics (built-in plugin)

When the `metrics` plugin is enabled, ToolAtlas exposes a `/metrics` endpoint at the API root:

```bash
export TOOLATLAS_PLUGINS="metrics"
```

```bash
curl http://localhost:8081/metrics
```

Exported metrics:

| Metric | Type | Labels |
|--------|------|--------|
| `toolatlas_calls_total` | Counter | `proxy`, `tool`, `status` |
| `toolatlas_call_duration_seconds` | Histogram | `proxy`, `tool` |
| `toolatlas_cache_hits_total` | Counter | `proxy` |
| `toolatlas_cache_misses_total` | Counter | `proxy` |

### 🔄 Background Registry Sync

Once enabled (built-in, no plugin needed), ToolAtlas periodically polls every connected MCP server for its current tool list. It:

1. Fetches the remote tool list via the shared `ConnectionManager`
2. Computes a SHA-256 hash of all tool definitions
3. Compares against the stored hash on the `Server` record
4. **If unchanged** — skips DB writes entirely
5. **If changed** — upserts new/updated tools, deletes removed ones, and auto-invalidates proxy caches

The sync runs every `TOOLATLAS_REGISTRY_SYNC_INTERVAL` seconds (default: 30). You can configure it:

```bash
export TOOLATLAS_REGISTRY_SYNC_INTERVAL=60
```

The sync only processes enabled servers. Disabled servers and connection failures are skipped gracefully with a warning log.

### 🔗 Shared ConnectionManager

All proxy engines now share a single `ConnectionManager` that maintains one `MCPClient` per `server_id`. Benefits:

- **Fewer connections** — 100 proxies all pointing to the same GitHub server share a single TCP connection
- **Auto-reconnect** — stale clients are detected and reconnected on next use
- **Graceful shutdown** — `connection_manager.close_all()` cleanly closes all clients

No configuration needed — this is enabled automatically.

---

## Configuration

Set via environment variables with `TOOLATLAS_` prefix. A `.env` file in the working directory is also loaded automatically.

| Variable | Default | Description |
|----------|---------|-------------|
| `TOOLATLAS_HOST` | `127.0.0.1` | Bind address |
| `TOOLATLAS_PORT` | `8081` | HTTP port (auto-increments if in use) |
| `TOOLATLAS_DATABASE_URL` | `sqlite+aiosqlite:///<data_dir>/toolatlas.db` | Database connection URL (any SQLAlchemy async dialect) |
| `TOOLATLAS_STORAGE_TYPE` | `json` | Storage backend (`json`, `sqlite`, or `postgres`) |
| `TOOLATLAS_DATA_DIR` | `~/.toolatlas` (Unix) / `%APPDATA%\ToolAtlas` (Win) | Data directory for databases and config |
| `TOOLATLAS_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `TOOLATLAS_BASE_PATH` | `""` | URL prefix when deployed behind a reverse proxy (e.g. `/toolatlas`) |
| `TOOLATLAS_REDIS_URL` | `""` | Redis URL for shared cache layer (e.g. `redis://localhost:6379/0`) |
| `TOOLATLAS_CACHE_TTL` | `300` | Cache TTL in seconds for proxy tool listings |
| `TOOLATLAS_REGISTRY_SYNC_INTERVAL` | `30` | Background sync interval in seconds |
| `TOOLATLAS_PLUGINS` | `[]` | Comma-separated list of plugin entry-point names or module paths to load |
| `TOOLATLAS_PLUGIN_DIRS` | `[]` | Comma-separated list of directories to scan for plugin modules |

When starting interactively, you'll be prompted for the data directory and storage type if the environment variables aren't set. If you choose `postgres`, you'll be prompted for the connection details (host, port, database name, username, password). You can also provide a `--database-url` flag or `TOOLATLAS_DATABASE_URL` env var to skip prompts.

### What's New in v3.0.0

| Area | Change | Impact |
|------|--------|--------|
| **ConnectionManager** | Shared `MCPClient` pool — one client per `server_id` reused across all proxies | Eliminates redundant connections; auto-reconnects stale clients; reduces total TCP connections |
| **Background Registry Sync** | Periodic SHA-256 sync of all upstream servers (default 30s) | Tools auto-discover, update, and remove without manual `discover`; stale detection is continuous |
| **Plugin Architecture** | Hook-based plugin system with `on_before_tool_call`, `on_after_tool_call`, `on_before_cache_lookup`, `on_tool_added`/`updated`/`removed` | Extend ToolAtlas without modifying core — built-in Cache + Metrics plugins included |
| **Cache Plugin (built-in)** | Memory→Redis two-tier cache with TTL jitter, warmup on startup, and stats | Redis as optional shared cache layer (`TOOLATLAS_REDIS_URL`); falls back to memory if unavailable |
| **Metrics Plugin (built-in)** | Prometheus-compatible counters for call count, latency, errors, cache hit ratio | `/metrics` endpoint for Prometheus scraping; no external dependencies beyond `prometheus-client` |
| **TTL Jitter** | Cache TTL randomly jittered by ±10% | Prevents thundering herd when multiple proxy TTLs expire simultaneously |

### What's New in v2.0.0

| Area | Change | Impact |
|------|--------|--------|
| **PostgreSQL** | Dialect-aware `connect_args`, `AsyncAdaptedQueuePool` (pool=10, overflow=20), early `asyncpg` import check | PostgreSQL now works reliably without crashes or per-query TCP overhead |
| **Transaction safety** | `commit()` wraps exceptions with `rollback()` — poisoned sessions are cleaned up | Eliminates `ResourceClosedError: This transaction is closed` errors |
| **Cache locking** | `list_tools` cache miss uses double-checked locking under `_engine_locks[slug]` | Prevents redundant `list_tools` flood when multiple domains' TTLs expire simultaneously |
| **Batch commits** | Proxy link-server tool disabling now uses `auto_commit=False` + single `commit()` | 130 toggles → 1 commit instead of 130 |
| **Stale detection** | Tool cache cleared immediately when any upstream client goes stale (not only when all are gone) | No stale tools returned after partial connection loss |
| **Import hygiene** | `from sqlalchemy import JSON` instead of `sqlalchemy.dialects.sqlite.JSON` | Cleaner, semantically correct for all dialects |

The CLI automatically scans for a free port (8080→8280) if the default port is occupied.

Example:

```bash
export TOOLATLAS_HOST=0.0.0.0
export TOOLATLAS_PORT=9000
export TOOLATLAS_STORAGE_TYPE=json
export TOOLATLAS_DATA_DIR=./toolatlas-dev
toolatlas start
```

To use non-interactive mode (no prompts):

```bash
TOOLATLAS_DATA_DIR=/custom/path TOOLATLAS_STORAGE_TYPE=json toolatlas start
```

### Using a `.env` file

Create a `.env` file in the directory where you run `toolatlas start`:

```env
TOOLATLAS_STORAGE_TYPE=postgres
TOOLATLAS_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/toolatlas
TOOLATLAS_DATA_DIR=./toolatlas-dev
```

Then simply run `toolatlas start` — all values are picked up automatically.

## Hosting ToolAtlas Inside an Existing Web Application

This guide explains how to embed ToolAtlas-MCP as a sub-app inside an existing Flask or FastAPI application under a URL prefix (e.g., `/toolatlas/`). No separate container or port is required.

### Prerequisites

- An existing Python web application (Flask or FastAPI) running behind a reverse proxy (nginx, Apache, etc.)
- Python 3.10+
- pip access to install the `toolatlas-mcp` package

### Installation

```bash
pip install toolatlas-mcp
```

This installs:
- `toolatlas-mcp` — the core package
- `aiosqlite` — SQLite async driver (needed even for JSON storage)
- `rich`, `typer` — CLI utilities
- `fastapi`, `uvicorn` — ASGI dependencies

For PostgreSQL, install with: `pip install "toolatlas-mcp[postgres]"`

### Storage Configuration

ToolAtlas stores its data (servers, tools, proxies, etc.) in a JSON file by default. Set these environment variables to control storage:

```bash
export TOOLATLAS_STORAGE_TYPE=json            # "json" (default), "sqlite", or "postgres"
export TOOLATLAS_DATABASE_URL=...             # required for "postgres", e.g. "postgresql+asyncpg://user:pass@host:5432/toolatlas"
export TOOLATLAS_DATA_DIR=/data/toolatlas     # custom data path, default ~/.toolatlas
```

If not set, data lives at `~/.toolatlas/data.json`.

### Integration

#### Option A: FastAPI (mount as sub-app)

```python
from fastapi import FastAPI
from toolatlas_mcp.api.app import create_app as create_toolatlas_app
from toolatlas_mcp.config import settings as toolatlas_settings
from toolatlas_mcp.db import init_db, close_db
from toolatlas_mcp.proxy.engine import close_all_engines

# Your existing FastAPI app
app = FastAPI()

# ... your existing routes ...

# Mount ToolAtlas under a prefix
toolatlas_settings.base_path = ""  # mount handles prefixing
toolatlas_app = create_toolatlas_app()
app.mount("/toolatlas", toolatlas_app)
```

Database lifecycle (add to your app's startup/shutdown):

```python
from contextlib import asynccontextmanager
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure data dir exists
    data_dir = os.environ.get("TOOLATLAS_DATA_DIR", "/data/toolatlas")
    os.makedirs(data_dir, exist_ok=True)
    await init_db()
    yield
    # Shutdown
    close_all_engines()
    await close_db()

app = FastAPI(lifespan=lifespan)
```

#### Option B: Flask (WSGI sub-app)

Flask does not natively support ASGI sub-mounts. Use ASGI middleware or run ToolAtlas as a separate ASGI app behind the same reverse proxy on a different path.

Example using werkzeug middleware (limited):

```python
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware

app = Flask(__name__)

# ... your existing Flask app ...

# ToolAtlas needs ASGI — use a wrapper or run separately
```

**Recommended for Flask:** Run ToolAtlas as a separate uvicorn process behind the same nginx, routing `/toolatlas/*` to it. Or migrate your Flask app to FastAPI to get native sub-app mounting.

### SPA Base URL Configuration

The ToolAtlas SPA reads the base path at runtime from `window.__TOOLATLAS_BASE_PATH__`, which is injected by the backend into the served `index.html`. Set `TOOLATLAS_BASE_PATH` (or use `--base-path`) to configure it:

```bash
# Environment variable
export TOOLATLAS_BASE_PATH=/toolatlas
toolatlas start

# Or CLI flag
toolatlas start --base-path /toolatlas
```

Both the Axios API client and React Router automatically use this value. **No JS bundle patching is required.**

### Reverse Proxy (nginx)

Add a location block in your nginx config:

```nginx
location /toolatlas/ {
    proxy_pass http://127.0.0.1:5100/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 86400s;
}
```

Reload nginx:

```bash
nginx -s reload
```

### Verifying the Deployment

```bash
# API health
curl http://localhost:5100/toolatlas/api/servers
curl http://localhost:5100/toolatlas/api/tools

# SPA
curl -o /dev/null -w '%{http_code}' http://localhost:5100/toolatlas/
# Expected: 200

# Open in browser
open http://localhost:5100/toolatlas/
```

### Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Blank page, no errors | React Router basename not configured | Set `TOOLATLAS_BASE_PATH` to match the reverse proxy prefix |
| API calls returning 404 | Axios baseURL not configured | Set `TOOLATLAS_BASE_PATH` to match the reverse proxy prefix |
| Data lost after restart | No persistent volume mounted | Set `TOOLATLAS_DATA_DIR` to a persisted path |
| SQLite file present even with JSON storage | ToolAtlas initializes both; safe to ignore or delete `.db` file after shutdown | — |

### Key Files

| File | Purpose |
|------|---------|
| `~/.toolatlas/data.json` | Default JSON data file |
| `~/.toolatlas/toolatlas.db` | SQLite DB (created even in JSON mode, can be deleted) |
| `site-packages/toolatlas_mcp/ui/dist/index.html` | SPA entry point (base path injected at runtime, no patching needed) |

### Notes

- ToolAtlas uses SQLAlchemy internally even for JSON storage. The `aiosqlite` dependency is required regardless of storage backend.
- The `data.json` file can grow large if many tool calls are recorded. Monitor its size if you enable call tracking.
- ToolAtlas SPA is a single-page application. Ensure your reverse proxy serves `index.html` for all sub-paths under `/toolatlas/` if you need direct URL entry (FastAPI mount handles this automatically).

---

## Client Examples

### Python

```python
import httpx, uuid

session_id = str(uuid.uuid4())
base = f"http://localhost:8081/proxy/dev/message/{session_id}"

# Initialize (required before any other call)
httpx.post(base, json={
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}
}).json()

httpx.post(base, json={"jsonrpc": "2.0", "method": "notifications/initialized"}).json()

# List available tools
tools = httpx.post(base, json={
    "jsonrpc": "2.0", "id": 2, "method": "list_tools"
}).json()
print(tools)

# Call a tool
result = httpx.post(base, json={
    "jsonrpc": "2.0", "id": 3, "method": "call_tool",
    "params": {"name": "search_code", "arguments": {"query": "auth"}}
}).json()
print(result)
```

### curl

```bash
SESSION_ID=$(uuidgen)

# Initialize
curl -s -X POST "http://localhost:8081/proxy/dev/message/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

curl -s -X POST "http://localhost:8081/proxy/dev/message/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# List tools
curl -s -X POST "http://localhost:8081/proxy/dev/message/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"list_tools"}'

# Call a tool
curl -s -X POST "http://localhost:8081/proxy/dev/message/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"call_tool","params":{"name":"search_code","arguments":{"query":"auth"}}}'
```

---

## Session Tracing (`_meta` Protocol)

ToolAtlas supports an **`_meta` protocol** for passing session context through the MCP proxy. This allows AI clients to correlate tool calls into traces, build span trees, and attach tenant/org context for governance.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `trace_id` | `str` (optional) | Groups calls into a single trace. Auto-generated if omitted. |
| `span_id` | `str` (optional) | Unique identifier for this call. Auto-generated via `uuid4()` if omitted. |
| `parent_span_id` | `str` (optional) | Links this call as a child of a previous span, building a span tree. |
| `org_id` | `str` (optional) | Organization identifier for multi-tenant deployments. |
| `tenant_id` | `str` (optional) | Tenant identifier (pass-through; enforcement via plugins). |
| `user_id` | `str` (optional) | End-user identifier who initiated the call. |

### Usage

Pass `_meta` alongside tool arguments in `call_tool`:

```python
import uuid

meta = {
    "trace_id": str(uuid.uuid4()),
    "span_id": str(uuid.uuid4()),
    "parent_span_id": previous_span_id,
    "org_id": "acme-corp",
    "tenant_id": "team-alpha",
}

result = await session.call_tool("search_code", {"query": "auth"}, _meta=meta)
```

- All calls sharing the same `trace_id` are grouped in the **Call Flow** tab.
- When `parent_span_id` is set, edges follow the parent–child hierarchy (span tree). Without it, edges are chronological.
- Tenant/org fields are stored on each call record and exposed via the API (`/api/analytics/calls?tenant_id=...`).

See [`examples/client/python_client.py`](examples/client/python_client.py) for a complete session tracing example.

---

## Docker

### Quick Start (SQLite/JSON Storage)

```bash
docker compose up --build
```

Opens ToolAtlas at `http://localhost:8081` with JSON file storage persisted in a Docker volume.

### PostgreSQL

```bash
docker compose -f docker-compose.postgres.yml up --build
```

Uses PostgreSQL 16 for production-grade storage, automatically initialized by ToolAtlas on startup.

### Configuration

Set environment variables via the `environment` key in `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `TOOLATLAS_HOST` | `0.0.0.0` | Bind address |
| `TOOLATLAS_PORT` | `8081` | HTTP port |
| `TOOLATLAS_STORAGE_TYPE` | `json` | `json` or `sqlite` |
| `TOOLATLAS_DATABASE_URL` | `sqlite+aiosqlite:////data/toolatlas.db` | Database URL |
| `TOOLATLAS_LOG_LEVEL` | `INFO` | Log level |
| `TOOLATLAS_BASE_PATH` | `` | Sub-path for reverse proxy |
| `TOOLATLAS_PLUGINS` | `` | Comma-separated plugin list |

### Volumes

- `toolatlas_data` — persisted JSON storage and SQLite database (Docker-managed volume)
- `postgres_data` — persisted PostgreSQL data (when using postgres compose file)

### Build from Source

```bash
docker build -t toolatlas-mcp .
docker run -p 8081:8081 -v toolatlas_data:/data toolatlas-mcp
```

---

## Development

```bash
git clone https://github.com/shashi3070/toolatlas-mcp
cd toolatlas-mcp

# Python
pip install -e ".[dev]"

# UI
cd ui && npm install && npm run build && cd ..

# Tests
pytest

# Dev server (API only, UI served by Vite on port 5173)
toolatlas start --reload
# In another terminal:
cd ui && npm run dev
```

---

## License

MIT © ToolAtlas contributors
