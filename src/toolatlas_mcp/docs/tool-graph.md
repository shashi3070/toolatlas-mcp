# Tool Graph

The Tool Graph visualizes the relationships between proxies, servers, and tools,
and provides call-flow traces and co-occurrence analysis.

## Graph Model

### Nodes

| Type | ID | Display Name | Status |
|------|----|-------------|--------|
| `proxy` | Proxy UUID | Proxy name | `"active"` |
| `server` | Server UUID | Server name | Connection status (`"connected"`, `"disconnected"`, `"unknown"`) |
| `tool` | Tool UUID | Tool name | (none) |

### Edges

| Type | Source | Target | Meaning |
|------|--------|--------|---------|
| `contains` | Proxy | Server | The proxy links to this server |
| `exposes` | Server | Tool | The server exposes this tool |

Example:

```
 ┌─────────────────────────────────────┐
 │         Proxy: "dev"                │
 │  contains ──┬── contains ──┬── ...  │
 │              │              │        │
 │              ▼              ▼        │
 │    Server: GitHub    Server: Jira    │
 │              │              │        │
 │    exposes ──┼── ─── exposes ─┤      │
 │              ▼              ▼        │
 │    Tool: search_code   Tool: issues  │
 └─────────────────────────────────────┘
```

## API Endpoints

### Get Full Graph

```
GET /api/graph
```

Returns all proxies, servers, tools, and their connections. No pagination (intended
for visualization tools that render the full topology).

**Response:**
```json
{
  "nodes": [
    {"id": "proxy-uuid", "type": "proxy", "name": "Developer", "status": "active"},
    {"id": "server-uuid", "type": "server", "name": "GitHub", "status": "connected"},
    {"id": "tool-uuid", "type": "tool", "name": "search_code"}
  ],
  "edges": [
    {"source": "proxy-uuid", "target": "server-uuid", "type": "contains"},
    {"source": "server-uuid", "target": "tool-uuid", "type": "exposes"}
  ]
}
```

### Get Proxy-Scoped Graph

```
GET /api/graph/proxy/{proxy_id}
```

Same structure as full graph, but only includes the specified proxy, its linked
servers, and their tools. Returns 404 if proxy not found.

### List Call Traces

```
GET /api/graph/traces?limit=50&proxy_id=optional
```

Returns aggregated trace summaries, ordered by most recent first.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `limit` | 50 | Max traces to return (1-500) |
| `proxy_id` | (none) | Filter to a specific proxy |

**Response:**
```json
[
  {
    "trace_id": "uuid",
    "tool_count": 3,
    "total_duration_ms": 4520.5,
    "first_timestamp": "2025-06-01T12:00:00",
    "last_timestamp": "2025-06-01T12:00:05",
    "success_rate": 100.0,
    "tool_names": ["search_issues", "get_issue", "search_pages"]
  }
]
```

### Get Single Trace Detail

```
GET /api/graph/trace/{trace_id}
```

Returns the full call sequence within a trace, with duration and success/failure
for each call. Returns 404 if trace not found.

**Response:**
```json
{
  "trace_id": "uuid",
  "nodes": [
    {"id": "call_0", "type": "call", "tool_name": "search_issues", "duration_ms": 1200.5, "success": true, "timestamp": "..."},
    {"id": "call_1", "type": "call", "tool_name": "get_issue", "duration_ms": 800.2, "success": true, "timestamp": "..."}
  ],
  "edges": [
    {"source": "call_0", "target": "call_1", "label": "800ms", "duration_ms": 800.2}
  ],
  "total_duration_ms": 2000.7,
  "tool_count": 2
}
```

### Get Tool Co-occurrence

```
GET /api/graph/co-occurrence?proxy_id=optional&min_count=2&limit=100
```

Analyzes which tools are frequently called together within the same trace.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `proxy_id` | (none) | Filter to a specific proxy |
| `min_count` | 2 | Minimum co-occurrence count for an edge to appear |
| `limit` | 100 | Max edges to return |

**Algorithm:**
1. Group all calls by trace_id
2. For each trace, collect unique tool names
3. Count pairwise co-occurrences within each trace
4. Return sorted by weight (descending)

**Response:**
```json
{
  "nodes": [
    {"id": "search_issues", "tool_name": "search_issues", "call_count": 42},
    {"id": "get_issue", "tool_name": "get_issue", "call_count": 38}
  ],
  "edges": [
    {"source": "search_issues", "target": "get_issue", "weight": 25}
  ]
}
```

## Trace Collection

Traces are collected automatically by the `ProxyMiddleware` class. Every tool call
is assigned a `trace_id` (UUID v4) and a sequence of events is recorded:

```python
# middleware.py:28-34
def add_event(event_type: str, description: str, details: dict | None = None):
    events.append({
        "type": event_type,
        "description": description,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
```

All events and the final call record are persisted to the `tool_calls` table:

```python
# middleware.py:55-66
await self.storage.record_call(
    tool_name=tool_name,
    proxy_id=proxy_id,
    tool_id=tool_id,
    server_id=server_id,
    request_args=request_args,
    duration_ms=duration_ms,
    success=success,
    error_message=error_message,
    client_id=client_id,
    trace_id=trace_id,
    events=events,
)
```

### Trace Lifecycle

```
1. proxy_message() receives JSON-RPC call
2. engine.call_tool() starts
3. middleware.track() begins → add_event("request_received")
4. engine resolves proxy → add_event("proxy_lookup")
5. engine resolves tool→server → add_event("tool_resolution")
6. engine forwards to server → add_event("server_call_start")
7. server responds → add_event("server_response")
8. engine returns result → add_event("response_returned")
9. middleware.track() ends → add_event("call_completed") → record_call()
```

## Visualization Tips

The graph endpoints are designed for use with D3.js, vis-network, or similar
graph visualization libraries:

- **Full graph** — Render as a force-directed layout with node colors by type
- **Trace graph** — Render as a timeline/flow chart showing call sequence
- **Co-occurrence** — Render as a weighted network showing tool relationships

Client-side styling suggestions:

| Node Type | Color | Shape |
|-----------|-------|-------|
| Proxy | Blue | Rounded rectangle |
| Server | Green | Rectangle |
| Tool | Gray | Circle |
| Call | Orange | Dot (in trace view) |
