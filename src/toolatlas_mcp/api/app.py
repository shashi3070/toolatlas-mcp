import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from toolatlas_mcp.api.routes import analytics, dashboard, glossary, graph, proxies, search, servers, settings, tools
from toolatlas_mcp import __version__
from toolatlas_mcp.config import settings as app_settings
from toolatlas_mcp.db import close_db, get_storage, init_db
from toolatlas_mcp.registry.storage import StorageBackend
from toolatlas_mcp.proxy.engine import close_all_engines
from toolatlas_mcp.services.connection_manager import connection_manager
from toolatlas_mcp.services.ws_manager import ws_manager

log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    base_path = app_settings.base_path
    app = FastAPI(
        title="ToolAtlas-MCP",
        version=__version__,
        description="ToolAtlas — Discover, Govern, and Optimize MCP Tools",
        root_path=base_path,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(servers.router)
    app.include_router(tools.router)
    app.include_router(proxies.router)
    app.include_router(glossary.router)
    app.include_router(analytics.router)
    app.include_router(dashboard.router)
    app.include_router(search.router)
    app.include_router(graph.router)
    app.include_router(settings.router)

    from toolatlas_mcp.proxy.server import router as proxy_router
    app.include_router(proxy_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": __version__}

    @app.websocket("/api/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await ws_manager.disconnect(websocket)

    ui_dirs = []
    if app_settings.ui_dir:
        ui_dirs.append(Path(app_settings.ui_dir))
    ui_dirs.append(Path(__file__).parent.parent / "ui" / "dist")
    for p in ui_dirs:
        if p.exists() and (p / "index.html").exists():
            app.mount("/", StaticFiles(directory=str(p), html=True), name="ui")
            log.info("Serving UI from %s", p)
            break

    _health_task: asyncio.Task[Any] | None = None
    _registry_task: asyncio.Task[Any] | None = None
    _warmup_storage = None
    _background_storages: list[StorageBackend] = []

    async def _create_storage():
        if app_settings.storage_type == "json":
            from toolatlas_mcp.registry.json_storage import JSONStorage
            from toolatlas_mcp.registry.storage import get_data_dir
            s = JSONStorage(get_data_dir() / "data.json")
            await s.load()
            return s
        else:
            from toolatlas_mcp.registry.repository import RegistryRepository
            from toolatlas_mcp.db import _get_session_factory
            factory = _get_session_factory()
            session = factory()
            return RegistryRepository(session)

    @app.on_event("startup")
    async def startup():
        nonlocal _health_task, _warmup_storage, _registry_task
        if app_settings.is_db_backend:
            await init_db()

        # Each background task gets its own storage (own DB session) to avoid
        # SQLAlchemy's "concurrent operations are not permitted" error.
        health_storage = await _create_storage()
        sync_storage = await _create_storage()
        _warmup_storage = await _create_storage()
        _background_storages.extend([health_storage, sync_storage, _warmup_storage])

        from toolatlas_mcp.services.health_checker import health_check_loop
        _health_task = asyncio.create_task(health_check_loop(health_storage))

        from toolatlas_mcp.services.registry_sync import RegistrySyncService
        _registry_task = asyncio.create_task(
            RegistrySyncService()._sync_loop(sync_storage, connection_manager)
        )

        from toolatlas_mcp.proxy.server import warmup_proxy_caches
        await warmup_proxy_caches(_warmup_storage)

        log.info("ToolAtlas-MCP started on %s:%s", app_settings.host, app_settings.port)

    @app.on_event("shutdown")
    async def shutdown():
        nonlocal _health_task, _warmup_storage, _registry_task
        if _registry_task:
            _registry_task.cancel()
            try:
                await _registry_task
            except (asyncio.CancelledError, Exception):
                pass
        if _health_task:
            _health_task.cancel()
            try:
                await _health_task
            except asyncio.CancelledError:
                pass
        for s in _background_storages:
            try:
                await s.close()
            except Exception:
                pass
        close_all_engines()
        await connection_manager.close_all()
        if app_settings.is_db_backend:
            await close_db()
        log.info("ToolAtlas-MCP stopped")

    return app
