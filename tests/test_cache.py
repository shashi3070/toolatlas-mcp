import time

import pytest
from unittest.mock import AsyncMock, patch

from toolatlas_mcp.plugin.builtins.cache import CachePlugin


@pytest.fixture
async def cache_plugin():
    """Memory-only cache plugin (no Redis)."""
    p = CachePlugin()
    await p.startup()
    yield p
    await p.shutdown()


@pytest.mark.asyncio
async def test_cache_hit_returns_data(cache_plugin):
    """4.1 Cached data is returned on lookup."""
    # Seed the memory cache directly
    slug = "dev"
    tools = [{"name": "tool_a"}]
    await cache_plugin.on_after_cache_lookup(slug, tools)

    result = await cache_plugin.on_before_cache_lookup(slug)
    assert result is not None
    assert result[1] == tools


@pytest.mark.asyncio
async def test_cache_miss_returns_none(cache_plugin):
    """4.2 Cache miss returns None."""
    result = await cache_plugin.on_before_cache_lookup("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_cache_invalidated(cache_plugin):
    """4.3 Invalidation removes cached entry."""
    slug = "dev"
    await cache_plugin.on_after_cache_lookup(slug, [{"name": "tool_a"}])
    await cache_plugin.on_cache_invalidated(slug)
    result = await cache_plugin.on_before_cache_lookup(slug)
    assert result is None


@pytest.mark.asyncio
async def test_cache_invalidated_unrelated_slug(cache_plugin):
    """4.6 Invalidating one slug doesn't affect another."""
    await cache_plugin.on_after_cache_lookup("dev", [{"name": "tool_a"}])
    await cache_plugin.on_after_cache_lookup("prod", [{"name": "tool_b"}])
    await cache_plugin.on_cache_invalidated("dev")

    dev_result = await cache_plugin.on_before_cache_lookup("dev")
    prod_result = await cache_plugin.on_before_cache_lookup("prod")
    assert dev_result is None
    assert prod_result is not None


@pytest.mark.asyncio
async def test_redis_fallback_memory_only():
    """3.8 Cache works in memory-only mode when Redis is unavailable."""
    with patch("toolatlas_mcp.plugin.builtins.cache.HAS_REDIS", False):
        p = CachePlugin()
        await p.startup()
        await p.on_after_cache_lookup("dev", [{"name": "tool_a"}])
        result = await p.on_before_cache_lookup("dev")
        assert result is not None
        await p.shutdown()


@pytest.mark.asyncio
async def test_multiple_proxies_independent_caches(cache_plugin):
    """4.6 Different slugs have independent caches."""
    await cache_plugin.on_after_cache_lookup("proxy_a", [{"name": "a1"}])
    await cache_plugin.on_after_cache_lookup("proxy_b", [{"name": "b1"}])

    a = await cache_plugin.on_before_cache_lookup("proxy_a")
    b = await cache_plugin.on_before_cache_lookup("proxy_b")
    assert a[1] == [{"name": "a1"}]
    assert b[1] == [{"name": "b1"}]
    assert a is not b
