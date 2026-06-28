# ToolAtlas UI Enhancement — Backend Implementation Plan

## Overview

Transform ToolAtlas from a CRUD management UI into a comprehensive NOC-style operations platform for MCP ecosystems. Auth/Users deferred to later phase.

## Phase 1 — Foundation (Dashboard, Enhanced Servers, Proxy Designer)

### 1.1 Server Model Enhancements
**Files:** `registry/models.py`, `api/schemas.py`, `registry/json_storage.py`, `registry/repository.py`, `registry/storage.py`

Add to `Server` model:
- `connection_status: str = "unknown"` — connected/disconnected/reconnecting/unknown
- `latency_ms: float | None = None` — last measured latency
- `reconnect_count: int = 0` — cumulative reconnection count
- `last_heartbeat: datetime | None = None` — last successful ping
- `last_tool_sync: datetime | None = None` — last tool discovery/sync

### 1.2 HealthChecker Service
**Files:** `services/__init__.py`, `services/health_checker.py`

- Background asyncio task running every 30s
- Pings each registered server via lightweight MCP initialize
- Updates server connection_status, latency_ms, last_heartbeat
- Increments reconnect_count on failure
- Emits events to WSManager for live UI updates

### 1.3 WebSocket Manager
**Files:** `services/__init__.py`, `services/ws_manager.py`

- `WSManager` — singleton managing connected WebSocket clients
- `broadcast(event_type, data)` — push typed events to all clients
- Event types: `server.status`, `call.new`, `alert.new`, `cache.updated`
- Endpoint: `GET /api/ws` (WebSocket upgrade)

### 1.4 Dashboard Summary Endpoint
**Files:** `api/routes/dashboard.py`

`GET /api/dashboard/summary` returns:
- `servers: { total, connected, disconnected, total_tools }`
- `proxies: { total }`
- `tools: { total }`
- `calls: { per_minute, total }`
- `cache: { hit_rate, entries }`
- `latency: { avg_ms }`
- `recent_alerts: [...]`
- `recent_activity: [...]`

### 1.5 Proxy Designer Endpoints
**Files:** `api/routes/proxies.py` (extend)

`GET /api/proxies/{id}/designer` — hierarchical view:
```json
{
  "proxy": { ... },
  "servers": [{
    "server": { ... },
    "tools": [{ "id", "name", "enabled", "alias", "custom_description" }]
  }]
}
```

`POST /api/proxies/{id}/designer/save` — batch save entire proxy configuration

### 1.6 Server Action Endpoints
**Files:** `api/routes/servers.py` (extend)

- `POST /api/servers/{id}/reconnect` — force reconnect, return status
- `POST /api/servers/{id}/ping` — lightweight health check, update stats

## Phase 2 — Developer Experience (Search, Graph, Tool Analytics)

### 2.1 Unified Search
**Files:** `services/search_service.py`, `api/routes/search.py`

`GET /api/search?q=...` — cross-entity search returning:
```json
{
  "servers": [...],
  "tools": [...],
  "proxies": [...],
  "glossary_terms": [...]
}
```

Uses PostgreSQL tsvector or SQLite LIKE depending on backend.

### 2.2 Graph View Endpoint
**Files:** `api/routes/graph.py`

`GET /api/graph` — full topology:
```json
{
  "nodes": [{ "id", "type", "name", "status" }],
  "edges": [{ "source", "target", "type" }]
}
```

`GET /api/graph/proxy/{id}` — zoomed proxy graph

### 2.3 Tool Analytics Endpoint
**Files:** `api/routes/analytics.py` (extend)

- `GET /api/analytics/top-tools?period=7d` — most called
- `GET /api/analytics/slowest-tools?period=7d` — highest avg latency
- `GET /api/analytics/error-rates?period=7d` — per-server/proxy error rates
- `GET /api/analytics/timeseries?metric=calls&interval=1h` — chart data

## Phase 3 — Operations (Cache, Settings, Alerts, AI, Enhanced Analytics)

### 3.1 Cache Management
**Files:** `services/cache_service.py`, `api/routes/cache.py`

Replace raw dict in `proxy/server.py` with `CacheService`:
- Tracks hits, misses, entries, refreshes, expired
- Optional Redis backend (`toolatlas-mcp[redis]`)
- `GET /api/cache/stats`, `POST /api/cache/invalidate`, `POST /api/cache/warm`

### 3.2 Runtime Settings
**Files:** `api/routes/settings.py`

- `GET /api/settings` — current runtime settings
- `PATCH /api/settings` — update settings
- Persisted to DB or JSON file

### 3.3 Alert System
**Files:** `registry/models.py` (Alert model), `services/alert_service.py`, `api/routes/alerts.py`

- Alert model: severity (info/warning/critical), title, message, source_type, source_id, status (active/acknowledged/resolved)
- Background evaluation via HealthChecker
- `GET /api/alerts`, `PATCH /api/alerts/{id}/acknowledge`, `PATCH /api/alerts/{id}/resolve`

### 3.4 AI Assistant
**Files:** `services/ai_service.py`, `api/routes/ai.py`

- `POST /api/ai/ask` — natural language query → system data → LLM → answer
- Configurable LLM provider (OpenAI, Anthropic, local via env vars)

### 3.5 Enhanced Analytics
**Files:** `api/routes/analytics.py` (extend), `services/metric_service.py`

- Time-series aggregation with configurable intervals
- Pre-computed rollups for performance

## Architecture Changes

### New directory: `src/toolatlas_mcp/services/`
Centralizes all background and cross-cutting logic.

### New directory: `src/toolatlas_mcp/api/middleware/` (deferred)
Auth middleware.

### Modified: `src/toolatlas_mcp/api/app.py`
- Register new route modules
- Start background health checker on startup
- Register WebSocket endpoint

### Modified: `src/toolatlas_mcp/proxy/middleware.py`
- Emit call events to WSManager for live feed

## Implementation Order

```
Week 1: Server model fields → HealthChecker → WSManager → Dashboard endpoint
Week 2: Proxy Designer → Server reconnect/ping → Search service
Week 3: Graph endpoint → Tool analytics → Cache service
Week 4: Alerts → Runtime settings → AI assistant → Enhanced analytics
```
