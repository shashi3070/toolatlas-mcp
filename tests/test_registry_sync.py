import asyncio
import hashlib
import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from toolatlas_mcp.services.registry_sync import _compute_tool_hash, RegistrySyncService


def _make_server(server_id="s1", name="Test", tool_hash=None):
    return {
        "id": server_id,
        "name": name,
        "enabled": True,
        "transport": "sse",
        "url": "http://localhost:9001",
        "tool_hash": tool_hash,
    }


def _make_tool(name="tool_a", description="A tool"):
    return {"name": name, "description": description, "inputSchema": {}}


class TestComputeToolHash:
    def test_hash_stable(self):
        h1 = _compute_tool_hash([_make_tool("a"), _make_tool("b")])
        h2 = _compute_tool_hash([_make_tool("a"), _make_tool("b")])
        assert h1 == h2

    def test_hash_changes_on_different_tools(self):
        assert _compute_tool_hash([_make_tool("a")]) != _compute_tool_hash([_make_tool("b")])

    def test_hash_independent_of_order(self):
        t1 = [_make_tool("a"), _make_tool("b")]
        t2 = [_make_tool("b"), _make_tool("a")]
        assert _compute_tool_hash(t1) == _compute_tool_hash(t2)


@pytest.mark.asyncio
async def test_sync_unchanged_tools():
    """2.1 Same hash → no DB changes."""
    mock_storage = AsyncMock(spec_set=["list_servers", "list_tools", "upsert_tool",
                                        "commit", "update_server", "delete_tool",
                                        "get_server", "list_proxies", "get_proxy_servers"])
    mock_storage.list_tools.return_value = [_make_tool("tool_a")]

    mock_cm = AsyncMock()
    mock_client = AsyncMock()
    mock_client.list_tools.return_value = [_make_tool("tool_a")]
    mock_cm.get_client.return_value = mock_client

    svc = RegistrySyncService()
    with patch("toolatlas_mcp.proxy.server.invalidate_proxies_for_server", AsyncMock()):
        result = await svc._sync_server(mock_storage, mock_cm, _make_server(tool_hash=_compute_tool_hash([_make_tool("tool_a")])))

    assert result["unchanged"] == ["tool_a"]
    mock_storage.upsert_tool.assert_not_called()


@pytest.mark.asyncio
async def test_sync_new_tool():
    """2.2 Server adds a tool → appears in DB."""
    mock_storage = AsyncMock(spec_set=["list_servers", "list_tools", "upsert_tool",
                                        "commit", "update_server", "delete_tool",
                                        "get_server", "list_proxies", "get_proxy_servers"])
    mock_storage.list_tools = AsyncMock(return_value=[])
    mock_storage.upsert_tool = AsyncMock(return_value={"id": "t1", "name": "tool_a", "enabled": True})
    mock_storage.commit = AsyncMock()
    mock_storage.update_server = AsyncMock()

    mock_cm = AsyncMock()
    mock_client = AsyncMock()
    mock_client.list_tools.return_value = [_make_tool("tool_a")]
    mock_cm.get_client.return_value = mock_client

    with patch("toolatlas_mcp.proxy.server.invalidate_proxies_for_server", AsyncMock()):
        svc = RegistrySyncService()
        result = await svc._sync_server(mock_storage, mock_cm, _make_server(tool_hash=""))

    assert result["added"] == ["tool_a"]
    mock_storage.upsert_tool.assert_awaited_once()
    mock_storage.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_removed_tool():
    """2.3 Server removes a tool → tool deleted from DB."""
    existing_tool = {"id": "t1", "name": "tool_a"}
    mock_storage = AsyncMock(spec_set=["list_servers", "list_tools", "upsert_tool",
                                        "commit", "update_server", "delete_tool",
                                        "get_server", "list_proxies", "get_proxy_servers"])
    mock_storage.list_tools = AsyncMock(return_value=[existing_tool])
    mock_storage.upsert_tool = AsyncMock(return_value=existing_tool)
    mock_storage.delete_tool = AsyncMock()
    mock_storage.commit = AsyncMock()
    mock_storage.update_server = AsyncMock()

    mock_cm = AsyncMock()
    mock_client = AsyncMock()
    mock_client.list_tools.return_value = []
    mock_cm.get_client.return_value = mock_client

    with patch("toolatlas_mcp.proxy.server.invalidate_proxies_for_server", AsyncMock()):
        svc = RegistrySyncService()
        result = await svc._sync_server(mock_storage, mock_cm, _make_server(tool_hash=""))

    assert result["removed"] == ["tool_a"]
    mock_storage.delete_tool.assert_awaited_once_with("t1")


@pytest.mark.asyncio
async def test_sync_updated_tool():
    """2.4 Server changes tool description → updated in DB."""
    existing_tool = {"id": "t1", "name": "tool_a", "description": "Old desc"}
    mock_storage = AsyncMock(spec_set=["list_servers", "list_tools", "upsert_tool",
                                        "commit", "update_server", "delete_tool",
                                        "get_server", "list_proxies", "get_proxy_servers"])
    mock_storage.list_tools = AsyncMock(return_value=[existing_tool])
    mock_storage.upsert_tool = AsyncMock(return_value=existing_tool)
    mock_storage.commit = AsyncMock()
    mock_storage.update_server = AsyncMock()

    mock_cm = AsyncMock()
    mock_client = AsyncMock()
    mock_client.list_tools.return_value = [_make_tool("tool_a", "New desc")]
    mock_cm.get_client.return_value = mock_client

    with patch("toolatlas_mcp.proxy.server.invalidate_proxies_for_server", AsyncMock()):
        svc = RegistrySyncService()
        result = await svc._sync_server(mock_storage, mock_cm, _make_server(tool_hash=""))

    assert result["updated"] == ["tool_a"]
    mock_storage.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_disabled_server_skipped():
    """2.5 Sync loop skips disabled servers."""
    mock_storage = AsyncMock()
    mock_storage.list_servers.return_value = [
        {"id": "s1", "name": "A", "enabled": False},
    ]
    mock_cm = AsyncMock()

    svc = RegistrySyncService()
    with patch.object(svc, "_sync_server", AsyncMock()) as mock_sync:
        try:
            await asyncio.wait_for(svc._sync_loop(mock_storage, mock_cm), timeout=0.5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        assert mock_sync.await_count == 0


@pytest.mark.asyncio
async def test_sync_server_connection_failure():
    """2.7 Connection failure → server skipped gracefully."""
    mock_storage = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.get_client.side_effect = Exception("Connection refused")

    svc = RegistrySyncService()
    result = await svc._sync_server(mock_storage, mock_cm, _make_server())

    assert result["added"] == []
    assert result["unchanged"] == []


@pytest.mark.asyncio
async def test_sync_loop_iterates_all_servers():
    """2.7 Sync loop calls _sync_server for each enabled server."""
    mock_storage = AsyncMock()
    mock_storage.list_servers.return_value = [
        _make_server(server_id="s1", name="A"),
        _make_server(server_id="s2", name="B"),
    ]

    mock_cm = AsyncMock()
    mock_client = AsyncMock()
    mock_client.list_tools.return_value = []
    mock_cm.get_client.return_value = mock_client

    svc = RegistrySyncService()
    with patch.object(svc, "_sync_server", AsyncMock(return_value={"added": [], "updated": [], "removed": [], "unchanged": []})) as mock_sync:
        try:
            await asyncio.wait_for(svc._sync_loop(mock_storage, mock_cm), timeout=0.5)
        except asyncio.TimeoutError:
            pass

    assert mock_sync.await_count >= 2
