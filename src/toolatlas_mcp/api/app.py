import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from toolatlas_mcp.api.routes import analytics, glossary, proxies, servers, tools
from toolatlas_mcp import __version__
from toolatlas_mcp.config import settings
from toolatlas_mcp.db import close_db, init_db

log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="ToolAtlas-MCP",
        version=__version__,
        description="ToolAtlas — Discover, Govern, and Optimize MCP Tools",
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

    from toolatlas_mcp.proxy.server import router as proxy_router
    app.include_router(proxy_router)

    ui_dirs = []
    if settings.ui_dir:
        ui_dirs.append(Path(settings.ui_dir))
    ui_dirs.append(Path(__file__).parent.parent / "ui" / "dist")
    for p in ui_dirs:
        if p.exists() and (p / "index.html").exists():
            app.mount("/", StaticFiles(directory=str(p), html=True), name="ui")
            log.info("Serving UI from %s", p)
            break

    @app.on_event("startup")
    async def startup():
        await init_db()
        log.info("ToolAtlas-MCP started on %s:%s", settings.host, settings.port)

    @app.on_event("shutdown")
    async def shutdown():
        await close_db()
        log.info("ToolAtlas-MCP stopped")

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": __version__}

    return app
