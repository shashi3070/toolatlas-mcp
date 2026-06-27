from __future__ import annotations

import json
import logging
import time
from typing import Any

from toolatlas_mcp.config import settings
from toolatlas_mcp.plugin.base import Plugin

try:
    import redis.asyncio as aioredis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

log = logging.getLogger(__name__)


class CachePlugin(Plugin):
    """Multi-tier cache plugin (memory -> Redis).

    Provides ``before_cache_lookup`` / ``after_cache_lookup`` hooks.
    When Redis is configured it runs as a two-tier cache: local memory
    is checked first, then Redis.  Writes propagate to both tiers.

    Configuration via ``TOOLATLAS_REDIS_URL`` env var (e.g.
    ``redis://localhost:6379/0``).  Falls back to memory-only when the
    variable is not set.
    """

    name = "cache"

    def __init__(self):
        self._memory: dict[str, tuple[float, Any]] = {}
        self._redis_client: Any = None
        self._redis_url: str = ""
        self._ttl: int = 300  # 5 minutes default

    async def startup(self):
        self._redis_url = getattr(settings, "redis_url", "") or ""
        self._ttl = getattr(settings, "cache_ttl", 300)
        if self._redis_url and HAS_REDIS:
            try:
                self._redis_client = aioredis.from_url(self._redis_url, decode_responses=True)
                await self._redis_client.ping()
                log.info("CachePlugin: connected to Redis at %s", self._redis_url)
            except Exception as e:
                log.warning("CachePlugin: Redis unavailable (%s), falling back to memory", e)
                self._redis_client = None
        else:
            log.info("CachePlugin: memory-only (set TOOLATLAS_REDIS_URL for Redis)")

    async def shutdown(self):
        if self._redis_client is not None:
            try:
                await self._redis_client.aclose()
            except Exception:
                pass

    async def on_before_cache_lookup(self, slug: str) -> tuple[float, list] | None:
        key = f"tools:{slug}"
        mem = self._memory.get(key)
        if mem is not None and not self._is_expired(mem):
            return mem
        if self._redis_client is not None:
            try:
                raw = await self._redis_client.get(key)
                if raw is not None:
                    data = json.loads(raw)
                    self._memory[key] = data
                    return data
            except Exception:
                pass
        return None

    async def on_after_cache_lookup(self, slug: str, tools: list) -> None:
        key = f"tools:{slug}"
        now = time.time()
        entry = (now, tools)
        self._memory[key] = entry
        if self._redis_client is not None:
            try:
                await self._redis_client.setex(key, self._ttl, json.dumps(entry))
            except Exception:
                pass

    async def on_cache_invalidated(self, slug: str) -> None:
        key = f"tools:{slug}"
        self._memory.pop(key, None)
        if self._redis_client is not None:
            try:
                await self._redis_client.delete(key)
            except Exception:
                pass

    @staticmethod
    def _is_expired(entry: tuple[float, Any], ttl: int = 60) -> bool:
        return time.time() - entry[0] > ttl


plugin = CachePlugin()
