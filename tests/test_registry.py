import pytest


@pytest.mark.asyncio
async def test_create_server(repo):
    server = await repo.create_server(name="TestServer", transport="sse", url="http://localhost:9999")
    assert server["name"] == "TestServer"
    assert server["transport"] == "sse"
    assert server["url"] == "http://localhost:9999"
    assert server["enabled"] is True


@pytest.mark.asyncio
async def test_list_servers(repo):
    await repo.create_server(name="S1", transport="sse", url="http://a:1")
    await repo.create_server(name="S2", transport="sse", url="http://b:2")
    servers = await repo.list_servers()
    assert len(servers) >= 2


@pytest.mark.asyncio
async def test_get_server(repo):
    s = await repo.create_server(name="GetMe", transport="sse", url="http://get:1")
    got = await repo.get_server(s["id"])
    assert got is not None
    assert got["name"] == "GetMe"


@pytest.mark.asyncio
async def test_update_server(repo):
    s = await repo.create_server(name="UpdateMe", transport="sse", url="http://u:1")
    updated = await repo.update_server(s["id"], name="UpdatedName", enabled=False)
    assert updated is not None
    assert updated["name"] == "UpdatedName"
    assert updated["enabled"] is False


@pytest.mark.asyncio
async def test_delete_server(repo):
    s = await repo.create_server(name="DeleteMe", transport="sse", url="http://d:1")
    deleted = await repo.delete_server(s["id"])
    assert deleted is True
    got = await repo.get_server(s["id"])
    assert got is None


@pytest.mark.asyncio
async def test_upsert_tool(repo):
    server = await repo.create_server(name="ToolServer", transport="sse", url="http://t:1")
    tool = await repo.upsert_tool(
        server_id=server["id"],
        name="test_tool",
        description="A test tool",
        input_schema={"type": "object", "properties": {}},
    )
    assert tool["name"] == "test_tool"
    assert tool["server_id"] == server["id"]

    tool2 = await repo.upsert_tool(
        server_id=server["id"],
        name="test_tool",
        description="Updated description",
        input_schema={},
    )
    assert tool2["id"] == tool["id"]
    assert tool2["description"] == "Updated description"


@pytest.mark.asyncio
async def test_proxy_crud(repo):
    proxy = await repo.create_proxy(name="Test Proxy", slug="test-proxy", description="Testing")
    assert proxy["name"] == "Test Proxy"
    assert proxy["slug"] == "test-proxy"

    by_slug = await repo.get_proxy_by_slug("test-proxy")
    assert by_slug is not None
    assert by_slug["id"] == proxy["id"]

    updated = await repo.update_proxy(proxy["id"], name="Updated Proxy")
    assert updated["name"] == "Updated Proxy"

    deleted = await repo.delete_proxy(proxy["id"])
    assert deleted is True


@pytest.mark.asyncio
async def test_proxy_server_linking(repo):
    server = await repo.create_server(name="LinkedServer", transport="sse", url="http://l:1")
    proxy = await repo.create_proxy(name="LinkedProxy", slug="linked")

    await repo.link_server_to_proxy(proxy["id"], server["id"])
    servers = await repo.get_proxy_servers(proxy["id"])
    assert len(servers) == 1
    assert servers[0]["id"] == server["id"]

    await repo.unlink_server_from_proxy(proxy["id"], server["id"])
    servers = await repo.get_proxy_servers(proxy["id"])
    assert len(servers) == 0


@pytest.mark.asyncio
async def test_glossary_crud(repo):
    domain = await repo.create_domain(name="Glossary Domain", description="For terms")
    term = await repo.create_glossary_term(domain_id=domain["id"], term="API", definition="Application Programming Interface")
    assert term["term"] == "API"

    terms = await repo.list_glossary_terms()
    assert len(terms) >= 1

    updated = await repo.update_glossary_term(term["id"], definition="Updated definition")
    assert updated["definition"] == "Updated definition"

    deleted = await repo.delete_glossary_term(term["id"])
    assert deleted is True


@pytest.mark.asyncio
async def test_domain_crud(repo):
    domain = await repo.create_domain(name="Security", description="Security-related tools")
    assert domain["name"] == "Security"

    domains = await repo.list_domains()
    assert len(domains) >= 1
