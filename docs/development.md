# Development Guide

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for UI development)
- Git

### Clone and Install

```bash
git clone <repo-url> toolatlas-mcp
cd toolatlas-mcp

# Install Python package in development mode
pip install -e ".[dev]"

# Install UI dependencies
cd ui
npm install
cd ..
```

### Running in Development

```bash
# Terminal 1: start the API server with auto-reload
toolatlas-mcp start --reload

# Terminal 2: start the UI dev server (optional, for UI work)
cd ui
npm run dev
```

The API server runs on `http://localhost:8081` by default.
The UI dev server runs on `http://localhost:5173` and proxies API calls.

## Code Layout

```
src/toolatlas_mcp/
├── api/
│   ├── app.py              # FastAPI application factory
│   ├── schemas.py          # Pydantic request/response models
│   └── routes/             # API route handlers
│       ├── analytics.py
│       ├── dashboard.py
│       ├── glossary.py
│       ├── graph.py
│       ├── proxies.py
│       ├── search.py
│       ├── servers.py
│       ├── settings.py
│       └── tools.py
├── cli/
│   └── main.py             # Typer CLI commands
├── config.py               # Settings class (env vars)
├── db.py                   # SQLAlchemy engine, session, Base
├── plugin/
│   ├── __init__.py         # Public API
│   ├── base.py             # Plugin base class + PluginContext
│   ├── manager.py          # PluginManager
│   └── builtins/
│       ├── cache.py        # CachePlugin
│       └── metrics.py      # MetricsPlugin
├── proxy/
│   ├── engine.py           # ProxyEngine (tool listing + call routing)
│   ├── middleware.py        # ProxyMiddleware (tracking + events)
│   └── server.py           # FastMCP proxy server
├── registry/
│   ├── mcp_client.py       # MCP client for upstream servers
│   ├── repository.py       # SQLAlchemy RegistryRepository
│   ├── storage.py          # StorageBackend interface + JSONStorage
│   └── sync.py             # RegistrySyncService
├── services/
│   ├── connection_manager.py # Shared MCP client connections
│   └── health_checker.py    # Server health pings
└── tracker/
    └── tracking.py          # Analytics tracking service

ui/
├── src/
│   ├── api/
│   │   └── client.ts       # API client (axios)
│   ├── pages/
│   │   ├── ProxyDetail.tsx  # Proxy designer page
│   │   └── ...              # Other pages
│   └── components/          # Reusable React components
└── package.json

tests/
├── conftest.py              # Pytest fixtures
├── fixtures/
│   ├── mcp_servers/         # Mock MCP servers
│   ├── servers_config.json   # Seed data for servers
│   ├── proxy_configs.json    # Seed data for proxies
│   └── glossary_terms.json   # Seed data for glossary
├── test_plugin.py           # Plugin system tests
├── test_proxy_engine.py     # Proxy engine tests
├── test_proxy_list_tools.py # API proxy listing tests
├── test_proxy_call_tool.py  # API proxy call tests
├── test_registry.py         # CRUD tests
├── test_registry_sync.py    # Sync tests
├── test_e2e.py              # End-to-end tests
├── test_graph.py            # Graph endpoint tests
├── test_analytics.py        # Analytics tests
└── ...                      # Other test files
```

## Testing Conventions

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_plugin.py -v

# Run with coverage
pytest --cov=toolatlas_mcp

# Run tests matching a keyword
pytest -k "alias or collision"
```

### Writing Tests

- Use `pytest-asyncio` for async tests (`@pytest.mark.asyncio`)
- Use `seeded_client` fixture for integration tests (in-memory DB + seed data)
- Use `unittest.mock` (`AsyncMock`, `patch`) for unit tests that avoid network calls
- Follow existing test patterns in `tests/`

### Adding a New API Route

1. Create a new file in `src/toolatlas_mcp/api/routes/`
2. Define a FastAPI `APIRouter` with your endpoints
3. Register the router in `api/app.py:create_app()`
4. Update `docs/api.md` with the new endpoint

### Adding a New Plugin Hook

1. Add the async method to the `Plugin` base class (`plugin/base.py`)
2. Add the dispatch to `PluginManager.execute()` or `execute_first()` calls in the code
3. Update the hook summary table in `docs/plugin-system.md`
4. Update `docs/plugin-hooks.md` with the firing location

### Adding a New Storage Method

1. Add the abstract method to `StorageBackend` (`registry/storage.py`)
2. Implement in `RegistryRepository` (`registry/repository.py`)
3. Implement in `JSONStorage` if needed (`registry/storage.py`)
4. Write tests in `tests/test_registry.py`

## Building the UI

```bash
cd ui
npm run build    # TypeScript check + Vite production build
npm run lint     # ESLint
npm run typecheck  # TypeScript compiler check only
```

The built files go to `src/toolatlas_mcp/ui/dist/`.

## Release Process

(Not yet automated — these are guidelines)

1. Update `CHANGELOG.md`
2. Bump version in `pyproject.toml`
3. Build: `python -m build`
4. Publish: `twine upload dist/*`
