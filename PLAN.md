# ToolAtlas-MCP — Build Plan

## Brand: ToolAtlas
## Package: `toolatlas-mcp`
## Tagline: Discover, Govern, and Optimize MCP Tools

---

## Architecture Overview

```
ToolAtlas Server — single process, multiple proxy endpoints
│
├── Proxy "Developer" ─── GitHub MCP ─── GitLab MCP
│   └── tools: search_code, read_file  (delete_repo disabled)
│
├── Proxy "PM" ────────── Jira MCP ─── Confluence MCP ─── GitHub MCP (read-only)
│   └── tools: search_issues, search_pages
│
├── Proxy "DevOps" ────── AWS MCP ─── K8s MCP ─── PagerDuty MCP
│   └── tools: all
│
└── Clients connect to http://host:port/proxy/{slug}
```

## Data Model

```
Proxy               Server              Tool                ProxyToolSetting
┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────────┐
│ id       │       │ id       │       │ id       │       │ proxy_id     │
│ name     │       │ name     │       │ server_id│       │ tool_id      │
│ slug     │◄──────│ transport│──────▶│ name     │       │ enabled      │
│ description│     │ command  │       │ description│     │ custom_desc  │
│ created  │       │ url      │       │ input_schema│    │ alias        │
└──────────┘       │ enabled  │       │ tags[]   │       └──────────────┘
                   └──────────┘       │ domain   │
                                      │ glossary_id│     GlossaryTerm
                     ProxyServer      └──────────┘     ┌──────────────┐
                     ┌──────────┐       ▲              │ id           │
                     │ proxy_id │       │              │ term         │
                     │ server_id│       │              │ definition   │
                     └──────────┘  Domain              │ tool_id?     │
                                   ┌──────────┐       └──────────────┘
                                   │ id       │
                                   │ name     │
                                   │ description│
                                   └──────────┘

ToolCall (auto-tracked)
┌──────────────────┐
│ id               │
│ proxy_id         │
│ tool_id          │
│ server_id        │
│ request_args     │
│ response_summary │
│ duration_ms      │
│ success          │
│ error_message    │
│ timestamp        │
│ client_id        │
└──────────────────┘
```

## How Tool Calls Flow

```
Claude → Proxy "Developer"
         │
         POST /proxy/developer/call_tool
         { "name": "search_code", "args": {"query": "auth"} }
         │
         ├── 1. Lookup proxy → get server mapping
         ├── 2. Check ProxyToolSetting.enabled
         ├── 3. Apply custom_description (for list_tools responses)
         ├── 4. @record: create ToolCall record (start time)
         ├── 5. Forward to backend MCP server
         ├── 6. @record: update ToolCall (duration, success, result)
         └── 7. Return result to Claude
```

## Phase 1 — Core MVP

| Component | Description |
|-----------|-------------|
| Database + Models | SQLAlchemy async, SQLite, auto-migration |
| Registry | Server + tool CRUD, MCP discovery (connect to server, import tools) |
| Proxy Engine | Intercept list_tools + call_tool, apply settings, track calls |
| REST API | FastAPI with all endpoints |
| Web UI | React + TypeScript SPA |
| CLI | `toolatlas start`, `toolatlas proxy add`, etc. |
| Test Fixtures | Mock MCP servers for E2E testing |

## Phase 2 — Analytics & Graph

- Tool call analytics (usage, latency, errors)
- Tool dependency graph
- Workflow discovery

## Phase 3 — Enterprise Governance

- RBAC, approval workflows, audit logs, secrets vault

## Project Structure

```
toolatlas-mcp/
├── pyproject.toml
├── PLAN.md
├── src/toolatlas_mcp/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli/main.py
│   ├── config.py
│   ├── db.py
│   ├── registry/
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── mcp_client.py
│   ├── proxy/
│   │   ├── engine.py
│   │   ├── server.py
│   │   └── middleware.py
│   ├── api/
│   │   ├── app.py
│   │   ├── schemas.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── proxies.py
│   │       ├── servers.py
│   │       ├── tools.py
│   │       ├── glossary.py
│   │       └── analytics.py
│   └── tracker/
│       └── service.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── api/client.ts
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── Proxies.tsx
│       │   ├── ProxyDetail.tsx
│       │   ├── Servers.tsx
│       │   ├── Tools.tsx
│       │   ├── ToolDetail.tsx
│       │   ├── Glossary.tsx
│       │   └── Analytics.tsx
│       └── components/
│           ├── Layout.tsx
│           ├── ToolCard.tsx
│           ├── SearchBar.tsx
│           └── StatusBadge.tsx
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── __init__.py
│   │   ├── mcp_servers/
│   │   │   ├── __init__.py
│   │   │   ├── github_mcp.py
│   │   │   ├── jira_mcp.py
│   │   │   ├── confluence_mcp.py
│   │   │   ├── aws_mcp.py
│   │   │   ├── pagerduty_mcp.py
│   │   │   └── slack_mcp.py
│   │   ├── servers_config.json
│   │   ├── proxy_configs.json
│   │   └── glossary_terms.json
│   ├── test_registry.py
│   ├── test_proxy_list_tools.py
│   ├── test_proxy_call_tool.py
│   ├── test_proxy_blocked_tool.py
│   ├── test_description_override.py
│   ├── test_glossary.py
│   ├── test_analytics.py
│   └── test_e2e.py
└── README.md
```
