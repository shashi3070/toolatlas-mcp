import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient


pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_alias_returned_in_tools_list(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    dev_proxy = [p for p in resp.json() if p["slug"] == "dev"][0]

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    tools = resp.json()
    assert len(tools) > 0
    tool = tools[0]

    assert "alias" in tool
    assert "original_name" in tool
    assert "name" in tool


@pytest.mark.asyncio
async def test_alias_returns_none_when_not_set(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    dev_proxy = [p for p in resp.json() if p["slug"] == "dev"][0]

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    tools = resp.json()
    tool = [t for t in tools if t["alias"] is None]
    if not tool:
        pytest.skip("All tools already have aliases set")
    tool = tool[0]

    assert tool["alias"] is None
    assert tool["name"] == tool["original_name"]


@pytest.mark.asyncio
async def test_set_alias_via_patch(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    dev_proxy = [p for p in resp.json() if p["slug"] == "dev"][0]

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    tools = resp.json()
    tool = [t for t in tools if t["alias"] is None]
    if not tool:
        pytest.skip("All tools already have aliases")
    tool = tool[0]

    resp = await seeded_client.patch(
        f"/api/proxies/{dev_proxy['id']}/tools/{tool['id']}",
        json={"alias": "test-alias-name"},
    )
    assert resp.status_code == 200
    assert resp.json()["alias"] == "test-alias-name"

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    updated = [t for t in resp.json() if t["id"] == tool["id"]][0]
    assert updated["alias"] == "test-alias-name"
    assert updated["name"] == "test-alias-name"
    assert updated["original_name"] == tool["original_name"]


@pytest.mark.asyncio
async def test_clear_alias_via_patch(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    dev_proxy = [p for p in resp.json() if p["slug"] == "dev"][0]

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    tools = resp.json()
    if not tools:
        pytest.skip("No tools found")
    tool = tools[0]

    await seeded_client.patch(
        f"/api/proxies/{dev_proxy['id']}/tools/{tool['id']}",
        json={"alias": "temp-alias"},
    )

    resp = await seeded_client.patch(
        f"/api/proxies/{dev_proxy['id']}/tools/{tool['id']}",
        json={"alias": ""},
    )
    assert resp.status_code == 200
    assert resp.json()["alias"] == ""

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    updated = [t for t in resp.json() if t["id"] == tool["id"]][0]
    assert updated["alias"] == ""
    assert updated["name"] == updated["original_name"]


@pytest.mark.asyncio
async def test_original_name_differs_from_name_when_alias_set(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    dev_proxy = [p for p in resp.json() if p["slug"] == "dev"][0]

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    tools = resp.json()
    tool = [t for t in tools if t["alias"] is None]
    if not tool:
        pytest.skip("All tools already have aliases")
    tool = tool[0]
    orig_name = tool["original_name"]

    await seeded_client.patch(
        f"/api/proxies/{dev_proxy['id']}/tools/{tool['id']}",
        json={"alias": "new-alias-name"},
    )

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    updated = [t for t in resp.json() if t["id"] == tool["id"]][0]
    assert updated["name"] == "new-alias-name"
    assert updated["original_name"] == orig_name


@pytest.mark.asyncio
async def test_alias_in_proxy_designer(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    dev_proxy = [p for p in resp.json() if p["slug"] == "dev"][0]

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/designer")
    assert resp.status_code == 200
    designer = resp.json()

    found_alias_field = False
    for server_entry in designer["servers"]:
        for tool in server_entry["tools"]:
            if "alias" in tool:
                found_alias_field = True
                break
    assert found_alias_field, "Designer response missing 'alias' field in tool entries"


@pytest.mark.asyncio
async def test_server_name_in_tools_list(seeded_client: AsyncClient):
    resp = await seeded_client.get("/api/proxies")
    dev_proxy = [p for p in resp.json() if p["slug"] == "dev"][0]

    resp = await seeded_client.get(f"/api/proxies/{dev_proxy['id']}/tools")
    tools = resp.json()
    assert len(tools) > 0
    for t in tools:
        assert "server_name" in t
        assert t["server_name"] in ("GitHub", "Jira", "Confluence")


@pytest.mark.asyncio
async def test_engine_collision_detection():
    """Test the collision detection logic in ProxyEngine.list_tools.
    
    Uses mocked MCP clients to simulate two servers with the same tool name.
    """
    from toolatlas_mcp.proxy.engine import ProxyEngine
    from toolatlas_mcp.registry.repository import RegistryRepository
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from toolatlas_mcp.db import Base

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        storage = RegistryRepository(session)
        server_a = await storage.create_server(name="ServerA", transport="sse", url="http://a.local")
        server_b = await storage.create_server(name="ServerB", transport="sse", url="http://b.local")

        for srv in (server_a, server_b):
            await storage.upsert_tool(server_id=srv["id"], name="get_info",
                                       description="Get info", input_schema={})

        proxy = await storage.create_proxy(name="CollisionTest", slug="collision-test",
                                            description="Test")
        for srv in (server_a, server_b):
            await storage.link_server_to_proxy(proxy["id"], srv["id"])
            tools = await storage.list_tools(server_id=srv["id"])
            for tool in tools:
                await storage.upsert_tool_setting(proxy["id"], tool["id"], enabled=True)

        p_engine = ProxyEngine(storage)

        mock_client_a = AsyncMock()
        mock_client_a.list_tools.return_value = [{"name": "get_info", "description": "From A"}]
        mock_client_b = AsyncMock()
        mock_client_b.list_tools.return_value = [{"name": "get_info", "description": "From B"}]

        side_effects = {server_a["id"]: mock_client_a, server_b["id"]: mock_client_b}
        actual_client = None

        async def fake_get_client(server):
            nonlocal actual_client
            actual_client = side_effects.get(server.get("id"))
            if not actual_client:
                raise RuntimeError("Unknown server")
            return actual_client

        with patch.object(
            p_engine.storage, "get_proxy_by_slug",
            return_value=proxy,
        ):
            with patch.object(
                p_engine.storage, "get_proxy_servers",
                return_value=[server_a, server_b],
            ):
                with patch(
                    "toolatlas_mcp.proxy.engine.connection_manager.get_client",
                    side_effect=fake_get_client,
                ):
                    result = await p_engine.list_tools("collision-test")

        assert len(result) == 2

        names = [r["name"] for r in result]
        assert "get_info" in names
        assert "get_info (ServerB)" in names

        info_a = [r for r in result if r["name"] == "get_info"][0]
        assert "From A" in info_a["description"]

        assert p_engine._tool_to_server["get_info"] == server_a["id"]
        assert p_engine._tool_to_server["get_info (ServerB)"] == server_b["id"]

    await engine.dispose()


@pytest.mark.asyncio
async def test_engine_alias_display_name():
    """Test alias is used as display_name in ProxyEngine.list_tools."""
    from toolatlas_mcp.proxy.engine import ProxyEngine
    from toolatlas_mcp.registry.repository import RegistryRepository
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from toolatlas_mcp.db import Base

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        storage = RegistryRepository(session)
        server = await storage.create_server(name="TestServer", transport="sse", url="http://test.local")
        await storage.upsert_tool(server_id=server["id"], name="my_tool",
                                   description="Original tool", input_schema={})

        proxy = await storage.create_proxy(name="AliasTest", slug="alias-test",
                                            description="Test")
        await storage.link_server_to_proxy(proxy["id"], server["id"])
        tools = await storage.list_tools(server_id=server["id"])
        await storage.upsert_tool_setting(proxy["id"], tools[0]["id"],
                                           enabled=True, alias="my-renamed-tool")

        p_engine = ProxyEngine(storage)

        mock_client = AsyncMock()
        mock_client.list_tools.return_value = [{"name": "my_tool", "description": "Original tool"}]

        with patch.object(p_engine.storage, "get_proxy_by_slug", return_value=proxy):
            with patch.object(p_engine.storage, "get_proxy_servers", return_value=[server]):
                with patch(
                    "toolatlas_mcp.proxy.engine.connection_manager.get_client",
                    return_value=mock_client,
                ):
                    result = await p_engine.list_tools("alias-test")

        assert len(result) == 1
        assert result[0]["name"] == "my-renamed-tool"
        assert p_engine._tool_to_server["my-renamed-tool"] == server["id"]

    await engine.dispose()


@pytest.mark.asyncio
async def test_engine_original_name_for_upstream():
    """Verify call_tool passes original_name to the upstream MCP client."""
    from toolatlas_mcp.proxy.engine import ProxyEngine
    from toolatlas_mcp.registry.repository import RegistryRepository
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from toolatlas_mcp.db import Base

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        storage = RegistryRepository(session)
        server = await storage.create_server(name="TestServer", transport="sse", url="http://test.local")
        await storage.upsert_tool(server_id=server["id"], name="original_tool_name",
                                   description="A tool", input_schema={})
        proxy = await storage.create_proxy(name="OrigNameTest", slug="orig-name-test",
                                            description="Test")
        await storage.link_server_to_proxy(proxy["id"], server["id"])
        tools = await storage.list_tools(server_id=server["id"])
        await storage.upsert_tool_setting(proxy["id"], tools[0]["id"],
                                           enabled=True, alias="renamed")

        p_engine = ProxyEngine(storage)
        p_engine._tool_to_server["renamed"] = server["id"]
        p_engine._tool_info["renamed"] = {"name": "original_tool_name", "description": "A tool"}

        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value={"content": "ok"})

        with patch.object(p_engine.storage, "get_proxy_by_slug", return_value=proxy):
            with patch.object(p_engine.storage, "get_proxy_servers", return_value=[server]):
                with patch(
                    "toolatlas_mcp.proxy.engine.connection_manager.get_client",
                    return_value=mock_client,
                ):
                    result = await p_engine.call_tool("orig-name-test", "renamed", {})

        assert result == {"content": "ok"}
        mock_client.call_tool.assert_awaited_once_with("original_tool_name", {}, meta={})

    await engine.dispose()
