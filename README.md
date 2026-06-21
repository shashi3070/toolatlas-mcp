# ToolAtlas-MCP

**The Control Plane for Your MCP Tools**

[![PyPI version](https://img.shields.io/pypi/v/toolatlas-mcp)](https://pypi.org/project/toolatlas-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/toolatlas-mcp)](https://pypi.org/project/toolatlas-mcp/)
[![License](https://img.shields.io/pypi/l/toolatlas-mcp)](LICENSE)

ToolAtlas sits between AI clients and MCP servers — giving you a **central registry**, **intelligent proxy**, **per-tool governance**, **usage analytics**, and a **web dashboard**.

```
pip install toolatlas-mcp
toolatlas start
```

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
│                 │     │  ┌──────────────┐  ┌─────────────┐ │     │  PagerDuty MCP   │
│                 │     │  │ Registry     │  │ Analytics   │ │     │  AWS MCP         │
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

## Features

![Dashboard](https://raw.githubusercontent.com/shashi3070/toolatlas-mcp/main/screenshots/dashboard.png)

### 🗂️ Proxy Groups — Organize Tools by Team or Purpose
Create proxies (named groups) and assign MCP servers to each. Every proxy exposes a different toolset.

```
Proxy "dev"    → GitHub + GitLab     (for developers)
Proxy "pm"     → Jira + Confluence   (for project managers)
Proxy "devops" → AWS + PagerDuty     (for operations)
```

Each proxy gets its own endpoint:

```
http://localhost:8080/proxy/dev/message/{session_id}
http://localhost:8080/proxy/pm/message/{session_id}
```

![Proxy Configuration](https://raw.githubusercontent.com/shashi3070/toolatlas-mcp/main/screenshots/proxy.png)

### 🛡️ Per-Tool Governance — Control What Each Proxy Exposes
Every tool can be independently configured **per proxy**:

| Control | What it does |
|---------|-------------|
| **Enable / Disable** | Block dangerous tools (e.g. `delete_repo`) without touching the server |
| **Custom Description** | Rewrite the tool's description so AI agents understand it in context |
| **Alias** | Rename the tool per proxy |

Example — same server, different proxy settings:

```
Proxy "dev":  ✓ search_code  ✓ create_repo  ✗ delete_repo  ✓ list_issues
Proxy "pm":   ✓ search_code  ✗ create_repo  ✗ delete_repo  ✓ list_issues (read-only)
```

![Tool Detail & Enrichment](https://raw.githubusercontent.com/shashi3070/toolatlas-mcp/main/screenshots/tool1.png)

### 🏷️ Tool Enrichment — Make Tools Smarter
Every registry tool can be enriched with business context. The enriched description is what clients see when they call `list_tools`:

| Enrichment | Purpose | Example in client view |
|---|---|---|
| **Custom Description** | Override the original server description | `Search for code in GitHub` |
| **Tags** | Add searchable labels | `Tags: git, code, search` |
| **Domain** | Categorize by business area | `Domain: development` |
| **Glossary Term** | Link to a business concept with definition | `Glossary: Search across all code repositories` |

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

---

## Installation

### Prerequisites

- **Python 3.10+** ([download](https://python.org/downloads))
- **pip** (comes with Python)

### Install from PyPI (recommended)

```bash
pip install toolatlas-mcp
```

Verify it installed:

```bash
toolatlas --help
```

You should see the CLI help with `start`, `server`, `proxy` commands.

### Install from source

```bash
git clone https://github.com/anomalyco/toolatlas-mcp
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
ToolAtlas-MCP starting on 127.0.0.1:8080
  Web UI: http://127.0.0.1:8080
  API:    http://127.0.0.1:8080/api/health
```

Open **http://localhost:8080** in your browser to see the dashboard.

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
- **Glossary Term** — link to a business term with definition

First create glossary terms and domains under the **Glossary** page, then assign them to tools.

### 7. Connect Your AI Client

Configure your MCP client (Claude Desktop, Cursor, custom agent) to point to ToolAtlas:

```
Type:     SSE
URL:      http://localhost:8080/proxy/dev/message/{session_id}
```

Each message gets a unique `session_id` (UUID). The proxy uses it to track call sequences.

#### Example: Python client

```python
import httpx
import uuid

session_id = str(uuid.uuid4())
proxy_url = f"http://localhost:8080/proxy/dev/message/{session_id}"

# List tools
resp = httpx.post(proxy_url, json={
    "jsonrpc": "2.0", "id": 1, "method": "list_tools"
})
print(resp.json())

# Call a tool
resp = httpx.post(proxy_url, json={
    "jsonrpc": "2.0", "id": 2, "method": "call_tool",
    "params": {"name": "search_code", "arguments": {"query": "auth"}}
})
print(resp.json())
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
| `toolatlas start` | Start the ToolAtlas server (default: `127.0.0.1:8080`) |
| `toolatlas start --port 9000 --host 0.0.0.0` | Start on a different address |
| `toolatlas start --reload` | Start with auto-reload (development) |
| `toolatlas server add <name>` | Register a new MCP server |
| `toolatlas server list` | List all registered servers |
| `toolatlas proxy add <slug>` | Create a new proxy |
| `toolatlas proxy list` | List all proxies |
| `toolatlas proxy link <slug> <server>` | Link a server to a proxy |

---

## Configuration

Set via environment variables with `TOOLATLAS_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `TOOLATLAS_HOST` | `127.0.0.1` | Bind address |
| `TOOLATLAS_PORT` | `8080` | HTTP port |
| `TOOLATLAS_DATABASE_URL` | `sqlite+aiosqlite:///toolatlas.db` | Database connection |
| `TOOLATLAS_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |

Example:

```bash
export TOOLATLAS_HOST=0.0.0.0
export TOOLATLAS_PORT=9000
export TOOLATLAS_LOG_LEVEL=DEBUG
toolatlas start
```

---

## Client Examples

### Python

```python
import httpx, uuid

session_id = str(uuid.uuid4())
base = f"http://localhost:8080/proxy/dev/message/{session_id}"

# List available tools
tools = httpx.post(base, json={
    "jsonrpc": "2.0", "id": 1, "method": "list_tools"
}).json()
print(tools)

# Call a tool
result = httpx.post(base, json={
    "jsonrpc": "2.0", "id": 2, "method": "call_tool",
    "params": {"name": "search_code", "arguments": {"query": "auth"}}
}).json()
print(result)
```

### curl

```bash
SESSION_ID=$(uuidgen)

# List tools
curl -s -X POST "http://localhost:8080/proxy/dev/message/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"list_tools"}'

# Call a tool
curl -s -X POST "http://localhost:8080/proxy/dev/message/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"call_tool","params":{"name":"search_code","arguments":{"query":"auth"}}}'
```

---

## Development

```bash
git clone https://github.com/anomalyco/toolatlas-mcp
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
