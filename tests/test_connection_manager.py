import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from toolatlas_mcp.services.connection_manager import ConnectionManager, connection_manager


@pytest.fixture(autouse=True)
async def reset_cm():
    await connection_manager.clear()
    yield
    await connection_manager.clear()


@pytest.fixture
def mock_mcp_client():
    with patch("toolatlas_mcp.services.connection_manager.MCPClient") as mock:
        instance = MagicMock()
        instance.connect = AsyncMock()
        instance.initialize = AsyncMock()
        instance.list_tools = AsyncMock(return_value=[{"name": "test_tool"}])
        instance.call_tool = AsyncMock(return_value={"content": [{"text": "done"}]})
        instance._listener_task = None
        instance.close = MagicMock()
        mock.return_value = instance
        yield instance


@pytest.mark.asyncio
async def test_get_client_creates_new(mock_mcp_client):
    """1.1 Creating a client for a new server returns a connected MCPClient."""
    server = {"id": "s1", "name": "Test", "transport": "sse", "url": "http://localhost:9001"}
    client = await connection_manager.get_client(server)
    assert client is mock_mcp_client
    mock_mcp_client.connect.assert_awaited_once()
    mock_mcp_client.initialize.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_client_reuses_existing(mock_mcp_client):
    """1.1 Getting client for same server returns the same instance."""
    server = {"id": "s1", "name": "Test", "transport": "sse", "url": "http://localhost:9001"}
    c1 = await connection_manager.get_client(server)
    c2 = await connection_manager.get_client(server)
    assert c1 is c2
    # connect/initialize called only once
    mock_mcp_client.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_different_servers_different_clients():
    """1.2 Different servers get different MCPClient instances."""
    call_count = 0

    def make_client(*a, **kw):
        nonlocal call_count
        call_count += 1
        inst = MagicMock()
        inst.connect = AsyncMock()
        inst.initialize = AsyncMock()
        inst._listener_task = None
        inst.close = MagicMock()
        return inst

    with patch("toolatlas_mcp.services.connection_manager.MCPClient", side_effect=make_client):
        s1 = {"id": "s1", "name": "A", "transport": "sse", "url": "http://a:9001"}
        s2 = {"id": "s2", "name": "B", "transport": "sse", "url": "http://b:9002"}
        c1 = await connection_manager.get_client(s1)
        c2 = await connection_manager.get_client(s2)
        assert c1 is not c2
        assert call_count == 2


@pytest.mark.asyncio
async def test_get_client_reconnects_stale(mock_mcp_client):
    """1.3 Stale client (reader done) is replaced with a new connection."""
    server = {"id": "s1", "name": "Test", "transport": "sse", "url": "http://localhost:9001"}
    c1 = await connection_manager.get_client(server)

    # Simulate stale
    c1._listener_task = AsyncMock()
    c1._listener_task.done.return_value = True

    with patch("toolatlas_mcp.services.connection_manager.MCPClient") as mock:
        instance2 = MagicMock()
        instance2.connect = AsyncMock()
        instance2.initialize = AsyncMock()
        instance2._listener_task = None
        instance2.close = MagicMock()
        mock.return_value = instance2

        c2 = await connection_manager.get_client(server)
        assert c2 is instance2
        assert c2 is not c1


@pytest.mark.asyncio
async def test_close_all_closes_all_clients(mock_mcp_client):
    """1.4 Close all should close every managed connection."""
    s1 = {"id": "s1", "name": "A", "transport": "sse", "url": "http://a:9001"}
    s2 = {"id": "s2", "name": "B", "transport": "sse", "url": "http://b:9002"}
    with patch("toolatlas_mcp.services.connection_manager.MCPClient") as mock:
        instances = []
        for _ in range(2):
            inst = MagicMock()
            inst.connect = AsyncMock()
            inst.initialize = AsyncMock()
            inst._listener_task = None
            inst.close = MagicMock()
            instances.append(inst)
        mock.side_effect = instances
        await connection_manager.get_client(s1)
        await connection_manager.get_client(s2)

    await connection_manager.close_all()
    for inst in instances:
        inst.close.assert_called_once()


@pytest.mark.asyncio
async def test_remove_client_removes_specific(mock_mcp_client):
    """1.6 Remove client by server_id."""
    server = {"id": "s1", "name": "Test", "transport": "sse", "url": "http://localhost:9001"}
    await connection_manager.get_client(server)
    await connection_manager.remove_client("s1")
    assert "s1" not in connection_manager._clients


@pytest.mark.asyncio
async def test_get_active_servers(mock_mcp_client):
    """1.5 get_active_servers returns connected server IDs."""
    s1 = {"id": "s1", "name": "A", "transport": "sse", "url": "http://a:9001"}
    s2 = {"id": "s2", "name": "B", "transport": "sse", "url": "http://b:9002"}
    with patch("toolatlas_mcp.services.connection_manager.MCPClient") as mock:
        instances = []
        for _ in range(2):
            inst = MagicMock()
            inst.connect = AsyncMock()
            inst.initialize = AsyncMock()
            inst._listener_task = None
            inst.close = MagicMock()
            instances.append(inst)
        mock.side_effect = instances
        await connection_manager.get_client(s1)
        await connection_manager.get_client(s2)

    active = connection_manager.get_active_servers()
    assert "s1" in active
    assert "s2" in active
    assert len(active) == 2


@pytest.mark.asyncio
async def test_multi_proxy_shares_client(mock_mcp_client):
    """1.5 Two proxies using same server share one MCPClient."""
    server = {"id": "s1", "name": "Shared", "transport": "sse", "url": "http://localhost:9001"}
    c1 = await connection_manager.get_client(server)
    c2 = await connection_manager.get_client(server)
    assert c1 is c2
