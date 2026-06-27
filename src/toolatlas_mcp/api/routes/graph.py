from datetime import datetime, timezone
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query

from toolatlas_mcp.api.schemas import (
    GraphNode, GraphEdge, GraphResponse,
    TraceNode, TraceEdge, TraceGraphResponse, TraceSummary,
    CoOccurrenceNode, CoOccurrenceEdge, CoOccurrenceResponse,
)
from toolatlas_mcp.db import get_storage
from toolatlas_mcp.registry.storage import StorageBackend

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("")
async def full_graph(storage: StorageBackend = Depends(get_storage)):
    servers = await storage.list_servers()
    proxies = await storage.list_proxies()
    tools = await storage.list_tools()

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    node_ids: set[str] = set()

    for proxy in proxies:
        pid = proxy.get("id", "")
        nodes.append(GraphNode(id=pid, type="proxy", name=proxy.get("name", ""), status="active"))
        node_ids.add(pid)

    for server in servers:
        sid = server.get("id", "")
        nodes.append(GraphNode(
            id=sid, type="server", name=server.get("name", ""),
            status=server.get("connection_status", "unknown"),
        ))
        node_ids.add(sid)

    for tool in tools:
        tid = tool.get("id", "")
        if tid not in node_ids:
            nodes.append(GraphNode(id=tid, type="tool", name=tool.get("name", "")))
            node_ids.add(tid)

    for tool in tools:
        edges.append(GraphEdge(
            source=tool.get("server_id", ""),
            target=tool.get("id", ""),
            type="exposes",
        ))

    for proxy in proxies:
        pid = proxy.get("id", "")
        proxy_servers = await storage.get_proxy_servers(pid)
        for s in proxy_servers:
            edges.append(GraphEdge(
                source=pid,
                target=s.get("id", ""),
                type="contains",
            ))

    return GraphResponse(nodes=nodes, edges=edges)


@router.get("/proxy/{proxy_id}")
async def proxy_graph(proxy_id: str, storage: StorageBackend = Depends(get_storage)):
    proxy = await storage.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    pid = proxy.get("id", "")
    nodes.append(GraphNode(id=pid, type="proxy", name=proxy.get("name", ""), status="active"))

    proxy_servers = await storage.get_proxy_servers(pid)
    for server in proxy_servers:
        sid = server.get("id", "")
        nodes.append(GraphNode(
            id=sid, type="server", name=server.get("name", ""),
            status=server.get("connection_status", "unknown"),
        ))
        edges.append(GraphEdge(source=pid, target=sid, type="contains"))

        server_tools = await storage.list_tools(server_id=sid)
        for tool in server_tools:
            tid = tool.get("id", "")
            nodes.append(GraphNode(id=tid, type="tool", name=tool.get("name", "")))
            edges.append(GraphEdge(source=sid, target=tid, type="exposes"))

    return GraphResponse(nodes=nodes, edges=edges)


# ── Call Flow Traces ────────────────────────────────────────────────────


@router.get("/traces")
async def list_traces(
    limit: int = Query(50, ge=1, le=500),
    proxy_id: str | None = Query(None),
    storage: StorageBackend = Depends(get_storage),
):
    calls = await storage.list_calls(limit=10000)
    if proxy_id:
        calls = [c for c in calls if c.get("proxy_id") == proxy_id]

    traces: dict[str, list[dict]] = defaultdict(list)
    for c in calls:
        tid = c.get("trace_id")
        if tid:
            traces[tid].append(c)

    result = []
    for tid, tcalls in traces.items():
        durations = [c.get("duration_ms", 0) for c in tcalls]
        success_count = sum(1 for c in tcalls if c.get("success", True))
        timestamps = [str(c["timestamp"]) for c in tcalls if c.get("timestamp")]
        tool_names = list(dict.fromkeys(c.get("tool_name", "?") for c in tcalls))
        result.append(TraceSummary(
            trace_id=tid,
            tool_count=len(tcalls),
            total_duration_ms=round(sum(durations), 2),
            first_timestamp=min(timestamps) if timestamps else None,
            last_timestamp=max(timestamps) if timestamps else None,
            success_rate=round(success_count / len(tcalls) * 100, 1),
            tool_names=tool_names,
        ))

    result.sort(key=lambda t: t.last_timestamp or "", reverse=True)
    return result[:limit]


@router.get("/trace/{trace_id}")
async def trace_graph(
    trace_id: str,
    storage: StorageBackend = Depends(get_storage),
):
    calls = await storage.list_calls(limit=10000)
    trace_calls = [c for c in calls if c.get("trace_id") == trace_id]
    if not trace_calls:
        raise HTTPException(404, "Trace not found")

    trace_calls.sort(key=lambda c: c.get("timestamp", ""))

    nodes: list[TraceNode] = []
    edges: list[TraceEdge] = []
    total_duration = sum(c.get("duration_ms", 0) for c in trace_calls)

    for i, c in enumerate(trace_calls):
        cid = c.get("id", f"call_{i}")
        ts = c.get("timestamp")
        nodes.append(TraceNode(
            id=cid,
            type="call",
            tool_name=c.get("tool_name", "unknown"),
            duration_ms=c.get("duration_ms", 0),
            success=c.get("success", True),
            timestamp=str(ts) if ts else None,
        ))
        if i > 0:
            prev_id = trace_calls[i - 1].get("id", f"call_{i - 1}")
            edges.append(TraceEdge(
                source=prev_id,
                target=cid,
                label=f"{c.get('duration_ms', 0):.0f}ms",
                duration_ms=c.get("duration_ms", 0),
            ))

    return TraceGraphResponse(
        trace_id=trace_id,
        nodes=nodes,
        edges=edges,
        total_duration_ms=round(total_duration, 2),
        tool_count=len(trace_calls),
    )


# ── Tool Co‑occurrence ──────────────────────────────────────────────────


@router.get("/co-occurrence")
async def co_occurrence(
    proxy_id: str | None = Query(None),
    min_count: int = Query(2, ge=1),
    limit: int = Query(100, ge=1, le=500),
    storage: StorageBackend = Depends(get_storage),
):
    calls = await storage.list_calls(limit=10000)
    if proxy_id:
        calls = [c for c in calls if c.get("proxy_id") == proxy_id]

    # Group by trace
    traces: dict[str, list[dict]] = defaultdict(list)
    for c in calls:
        tid = c.get("trace_id")
        if tid:
            traces[tid].append(c)

    # Per-trace unique tool usage
    tool_counts: dict[str, int] = defaultdict(int)
    for tcalls in traces.values():
        seen: set[str] = set()
        for c in tcalls:
            name = c.get("tool_name", "unknown")
            if name not in seen:
                tool_counts[name] += 1
                seen.add(name)

    # Pairwise co-occurrence
    cooc: dict[tuple[str, str], int] = defaultdict(int)
    for tcalls in traces.values():
        tcalls.sort(key=lambda c: c.get("timestamp", ""))
        unique = list(dict.fromkeys(c.get("tool_name", "unknown") for c in tcalls))
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                a, b = unique[i], unique[j]
                key = (a, b) if a < b else (b, a)
                cooc[key] += 1

    tool_counts = dict(sorted(tool_counts.items(), key=lambda x: -x[1]))
    nodes = [CoOccurrenceNode(id=n, tool_name=n, call_count=c) for n, c in tool_counts.items()]

    node_set = set(tool_counts.keys())
    edges = [
        CoOccurrenceEdge(source=a, target=b, weight=w)
        for (a, b), w in sorted(cooc.items(), key=lambda x: -x[1])
        if a in node_set and b in node_set and w >= min_count
    ][:limit]

    return CoOccurrenceResponse(nodes=nodes, edges=edges)
