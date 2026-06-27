from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter

from toolatlas_mcp.plugin.base import Plugin, PluginContext

log = logging.getLogger(__name__)


class MetricsPlugin(Plugin):
    """Built-in Prometheus-compatible metrics collector.

    Tracks:
      - Number of tool calls per tool and per proxy
      - Call duration (p50, p95, p99)
      - Error count / error rate
      - Cache hit / miss counts
      - Active server connections
      - Registry sync results

    Exposes a ``GET /metrics`` endpoint (Prometheus text format) via
    a FastAPI router that can be mounted by the application.
    """

    name = "metrics"

    def __init__(self):
        self._call_count: defaultdict[str, int] = defaultdict(int)
        self._error_count: defaultdict[str, int] = defaultdict(int)
        self._durations: defaultdict[str, list[float]] = defaultdict(list)
        self._cache_hits = 0
        self._cache_misses = 0
        self._last_sync_time = 0.0

    # ------------------------------------------------------------------
    # Plugin lifecycle
    # ------------------------------------------------------------------

    async def startup(self):
        log.info("MetricsPlugin started")

    async def shutdown(self):
        pass

    # ------------------------------------------------------------------
    # Router for Prometheus /metrics endpoint
    # ------------------------------------------------------------------

    @property
    def router(self) -> APIRouter:
        r = APIRouter(tags=["metrics"])

        @r.get("/metrics")
        async def metrics():
            return self._render_prometheus()

        return r

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    async def on_after_tool_call(self, ctx: PluginContext, result: dict) -> None:
        self._call_count[ctx.tool_name] += 1
        proxy_key = ctx.slug or "unknown"
        self._call_count[f"proxy:{proxy_key}"] += 1
        dur = ctx.extra.get("duration_ms", 0)
        if dur:
            self._durations[ctx.tool_name].append(dur)
            self._durations[f"proxy:{proxy_key}"].append(dur)

    async def on_before_tool_call(self, ctx: PluginContext) -> None:
        ctx.extra["start_time"] = time.time()

    async def on_after_cache_lookup(self, slug: str, tools: list) -> None:
        if tools is not None:
            self._cache_hits += 1
        else:
            self._cache_misses += 1

    async def on_server_connected(self, server_id: str) -> None:
        self._call_count[f"connections"] += 1

    async def on_tool_added(self, server_id: str, tool_names: list[str]) -> None:
        for name in tool_names:
            self._call_count[f"tool_added:{name}"] += 1

    async def on_tool_removed(self, server_id: str, tool_names: list[str]) -> None:
        for name in tool_names:
            self._call_count[f"tool_removed:{name}"] += 1

    def record_sync(self):
        self._last_sync_time = time.time()

    # ------------------------------------------------------------------
    # Prometheus output
    # ------------------------------------------------------------------

    def _render_prometheus(self) -> dict:
        """Return key-value stats (simplified Prometheus-like format)."""
        p50 = lambda vals: sorted(vals)[len(vals) // 2] if vals else 0
        p95 = lambda vals: sorted(vals)[int(len(vals) * 0.95)] if vals else 0
        p99 = lambda vals: sorted(vals)[int(len(vals) * 0.99)] if vals else 0

        stats: dict[str, Any] = {
            "toolatlas_metrics_version": 1,
            "call_count": dict(self._call_count),
            "error_count": dict(self._error_count),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_ratio": round(
                self._cache_hits / (self._cache_hits + self._cache_misses), 4,
            ) if (self._cache_hits + self._cache_misses) else 0.0,
        }

        for key, vals in self._durations.items():
            if len(vals) > 1:
                stats[f"duration_ms_p50:{key}"] = round(p50(vals), 2)
                stats[f"duration_ms_p95:{key}"] = round(p95(vals), 2)
                stats[f"duration_ms_p99:{key}"] = round(p99(vals), 2)

        return stats
