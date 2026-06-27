import asyncio
import json
import os
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from toolatlas_mcp.api.app import create_app
from toolatlas_mcp.config import settings
from toolatlas_mcp.db import Base, get_db, get_storage
from toolatlas_mcp.registry.repository import RegistryRepository
from tests.fixtures.mcp_servers.aws_mcp import AWSMCPServer
from tests.fixtures.mcp_servers.confluence_mcp import ConfluenceMCPServer
from tests.fixtures.mcp_servers.github_mcp import GitHubMCPServer
from tests.fixtures.mcp_servers.jira_mcp import JiraMCPServer
from tests.fixtures.mcp_servers.pagerduty_mcp import PagerDutyMCPServer
from tests.fixtures.mcp_servers.slack_mcp import SlackMCPServer

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_mcp_servers: list = []


def load_json(filename: str):
    with open(FIXTURES_DIR / filename) as f:
        return json.load(f)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def repo(db_session) -> RegistryRepository:
    return RegistryRepository(db_session)


@pytest_asyncio.fixture(scope="session")
def start_mcp_servers():
    global _mcp_servers
    servers = [
        GitHubMCPServer(port=9001),
        JiraMCPServer(port=9002),
        ConfluenceMCPServer(port=9003),
        AWSMCPServer(port=9004),
        PagerDutyMCPServer(port=9005),
        SlackMCPServer(port=9006),
    ]
    for s in servers:
        s.start()
        _mcp_servers.append(s)
    yield
    for s in _mcp_servers:
        s.stop()


async def _seed_server_with_tools(repo, sc):
    server = await repo.create_server(
        name=sc["name"],
        transport=sc["transport"],
        url=sc["url"],
    )
    for tc in sc.get("tools", []):
        await repo.upsert_tool(
            server_id=server["id"],
            name=tc["name"],
            description=tc.get("description", ""),
            input_schema=tc.get("input_schema", {}),
        )
    return server


@pytest_asyncio.fixture
async def seed_registry(repo):
    servers_config = load_json("servers_config.json")
    for sc in servers_config:
        await _seed_server_with_tools(repo, sc)
    return repo


@pytest_asyncio.fixture
async def seed_proxies(repo):
    proxy_configs = load_json("proxy_configs.json")
    servers_config = load_json("servers_config.json")

    server_map = {}
    for sc in servers_config:
        server = await _seed_server_with_tools(repo, sc)
        server_map[sc["name"]] = server

    for pc in proxy_configs:
        proxy = await repo.create_proxy(
            name=pc["name"],
            slug=pc["slug"],
            description=pc["description"],
        )
        for server_name in pc["servers"]:
            server = server_map.get(server_name)
            if server:
                await repo.link_server_to_proxy(proxy["id"], server["id"])

                tools = await repo.list_tools(server_id=server["id"])
                for tool in tools:
                    overrides = pc["tool_overrides"].get(tool["name"], {})
                    await repo.upsert_tool_setting(
                        proxy_id=proxy["id"],
                        tool_id=tool["id"],
                        enabled=overrides.get("enabled", True),
                        custom_description=overrides.get("custom_description"),
                        alias=overrides.get("alias"),
                    )
    return repo, server_map


@pytest_asyncio.fixture
async def client(db_engine):
    app = create_app()

    async def override_get_storage():
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            yield RegistryRepository(session)

    app.dependency_overrides[get_storage] = override_get_storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seeded_client():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        repo = RegistryRepository(session)
        servers_config = load_json("servers_config.json")
        server_map = {}
        for sc in servers_config:
            server = await _seed_server_with_tools(repo, sc)
            server_map[sc["name"]] = server

        proxy_configs = load_json("proxy_configs.json")
        for pc in proxy_configs:
            proxy = await repo.create_proxy(
                name=pc["name"],
                slug=pc["slug"],
                description=pc["description"],
            )
            for server_name in pc["servers"]:
                server = server_map.get(server_name)
                if server:
                    await repo.link_server_to_proxy(proxy["id"], server["id"])
                    tools = await repo.list_tools(server_id=server["id"])
                    for tool in tools:
                        overrides = pc["tool_overrides"].get(tool["name"], {})
                        await repo.upsert_tool_setting(
                            proxy_id=proxy["id"],
                            tool_id=tool["id"],
                            enabled=overrides.get("enabled", True),
                        )

        domain = await repo.create_domain(name="Engineering", description="Software engineering domain")
        glossary = load_json("glossary_terms.json")
        for gt in glossary:
            await repo.create_glossary_term(domain_id=domain["id"], term=gt["term"], definition=gt["definition"])

    async def override_get_storage():
        async with session_factory() as session:
            yield RegistryRepository(session)

    app.dependency_overrides[get_storage] = override_get_storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await engine.dispose()
