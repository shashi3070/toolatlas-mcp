# API Reference

All REST endpoints are prefixed with `/api` and served by FastAPI.

Base URL: `http://localhost:8081/api`

## Servers

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/servers` | List all registered servers |
| `POST` | `/servers` | Register a new MCP server |
| `GET` | `/servers/{id}` | Get server details |
| `PATCH` | `/servers/{id}` | Update server configuration |
| `DELETE` | `/servers/{id}` | Delete a server |
| `POST` | `/servers/discover-preview` | Preview tools without saving |
| `POST` | `/servers/{id}/ping` | Check server connectivity |
| `POST` | `/servers/{id}/reconnect` | Force server reconnection |
| `POST` | `/servers/{id}/discover` | Discover and save tools from server |

### POST /servers

```json
{
  "name": "GitHub",
  "transport": "sse",
  "url": "http://github-mcp.local:8000",
  "command": null
}
```

### POST /servers/discover-preview

```json
{
  "transport": "sse",
  "url": "http://github-mcp.local:8000",
  "command": null
}
```

Response: `[{"name": "search_code", "description": "...", "input_schema": {...}}]`

## Tools

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tools` | List all tools (with optional `server_id`, `domain`, `search` filters) |
| `GET` | `/tools/{id}` | Get tool details |
| `PATCH` | `/tools/{id}` | Update tool metadata (description, tags, domain, enabled, glossary) |
| `DELETE` | `/tools/{id}` | Delete a tool |
| `POST` | `/tools/{id}/test` | Test a tool by calling the upstream server |

### GET /tools

Query parameters:
- `server_id` (optional) — Filter by server
- `domain` (optional) — Filter by domain
- `search` (optional) — Search name/description

### POST /tools/{id}/test

```json
{"arguments": {"query": "search term"}}
```

Response:
```json
{"name": "search_code", "result": {"content": [...]}, "duration_ms": 1520.5}
```

On error:
```json
{"name": "search_code", "error": "Connection refused", "duration_ms": 5000.0}
```

## Proxies

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/proxies` | List all proxies |
| `POST` | `/proxies` | Create a new proxy |
| `GET` | `/proxies/{id}` | Get proxy details |
| `PATCH` | `/proxies/{id}` | Update proxy (name, slug, description) |
| `DELETE` | `/proxies/{id}` | Delete a proxy |

### POST /proxies

```json
{
  "name": "Developer",
  "slug": "dev",
  "description": "Tools for developers"
}
```

### Proxy Servers

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/proxies/{id}/servers` | List servers linked to proxy |
| `POST` | `/proxies/{id}/servers` | Link a server (optionally select tools) |
| `DELETE` | `/proxies/{id}/servers/{server_id}` | Unlink a server |

### POST /proxies/{id}/servers

```json
{
  "server_id": "uuid",
  "tool_names": ["search_code", "list_issues"]
}
```

Omitting `tool_names` includes all tools from the server.

### Proxy Tools

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/proxies/{id}/tools` | List proxy tools with enrichment + alias resolution |
| `PATCH` | `/proxies/{id}/tools/{tool_id}` | Update tool setting (enabled, alias, custom_description) |

### GET /proxies/{id}/tools

Returns tools with per-proxy settings applied:
```json
[
  {
    "id": "uuid",
    "server_id": "uuid",
    "name": "find-code",
    "original_name": "search_code",
    "alias": "find-code",
    "description": "Search code across repos\nDomain: Engineering",
    "input_schema": {...},
    "enabled": true,
    "tags": ["search"],
    "domain": ["Engineering"],
    "glossary_term_ids": ["uuid"],
    "server_name": "GitHub"
  }
]
```

### PATCH /proxies/{id}/tools/{tool_id}

```json
{"alias": "find-code", "custom_description": "Custom desc", "enabled": true}
```

### Proxy Designer

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/proxies/{id}/designer` | Get proxy designer state (servers + tools with settings) |
| `POST` | `/proxies/{id}/designer/save` | Save designer changes in bulk |

### Proxy Stats

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/proxies/{id}/stats` | Get proxy-specific analytics |

## Analytics

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/analytics/stats` | Aggregated call statistics |
| `GET` | `/analytics/calls` | List call records (with proxy_id, tool_id, limit, offset filters) |
| `GET` | `/analytics/calls/{id}` | Get single call detail with events |
| `GET` | `/analytics/top-tools` | Most-called tools |
| `GET` | `/analytics/slowest-tools` | Tools with highest average latency |
| `GET` | `/analytics/error-rates` | Overall error rate |

## Graph

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/graph` | Full topology graph (all proxies, servers, tools) |
| `GET` | `/graph/proxy/{id}` | Proxy-scoped graph |
| `GET` | `/graph/traces` | List call traces (query: `limit`, `proxy_id`) |
| `GET` | `/graph/trace/{id}` | Single trace detail with call sequence |
| `GET` | `/graph/co-occurrence` | Tool co-occurrence analysis (query: `proxy_id`, `min_count`, `limit`) |

## Glossary

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/glossary/terms` | List all glossary terms |
| `POST` | `/glossary/terms` | Create a glossary term |
| `GET` | `/glossary/terms/{id}` | Get term details |
| `PATCH` | `/glossary/terms/{id}` | Update term |
| `DELETE` | `/glossary/terms/{id}` | Delete term |
| `GET` | `/glossary/domains` | List all domains |
| `POST` | `/glossary/domains` | Create a domain |
| `PATCH` | `/glossary/domains/{id}` | Update domain |
| `DELETE` | `/glossary/domains/{id}` | Delete domain |
| `POST` | `/glossary/import` | Bulk import terms |

## Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (returns `{"status": "ok"}`) |

## Search

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/search?q=term` | Unified search across tools, servers, glossary |

## Dashboard

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/dashboard` | Dashboard summary with counts and stats |
