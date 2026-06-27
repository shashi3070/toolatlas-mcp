from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from toolatlas_mcp.config import settings
from toolatlas_mcp.registry.storage import StorageBackend, get_data_dir


class Base(DeclarativeBase):
    pass


def _get_is_pg() -> bool:
    return settings.database_url.startswith("postgresql")


def _ensure_pg_driver():
    if _get_is_pg():
        try:
            import asyncpg  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "asyncpg is required for PostgreSQL. "
                "Install with: pip install 'toolatlas-mcp[postgres]'"
            )


def _create_engine():
    is_pg = _get_is_pg()
    engine_kwargs: dict = {
        "echo": False,
        "connect_args": {"command_timeout": 10} if is_pg else {"timeout": 10},
    }
    if is_pg:
        engine_kwargs["poolclass"] = AsyncAdaptedQueuePool
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20
    else:
        engine_kwargs["poolclass"] = NullPool
    return create_async_engine(settings.database_url, **engine_kwargs)


_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        _ensure_pg_driver()
        _engine = _create_engine()
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(_get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncSession:
    factory = _get_session_factory()
    async with factory() as session:
        yield session


async def get_storage() -> AsyncGenerator[StorageBackend, None]:
    if settings.storage_type == "json":
        from toolatlas_mcp.registry.json_storage import JSONStorage

        json_path = get_data_dir() / "data.json"
        storage = JSONStorage(json_path)
        await storage.load()
        try:
            yield storage
        finally:
            await storage.save()
            await storage.close()
    else:
        from toolatlas_mcp.registry.repository import RegistryRepository

        factory = _get_session_factory()
        async with factory() as session:
            yield RegistryRepository(session)


async def init_db():
    engine = _get_engine()
    async with engine.begin() as conn:
        from toolatlas_mcp.registry.models import Base as RegistryBase
        await conn.run_sync(RegistryBase.metadata.create_all)
    dialect = engine.dialect.name
    if dialect == "sqlite":
        async with engine.connect() as conn:
            await conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
            await conn.exec_driver_sql("PRAGMA busy_timeout=10000;")
    elif dialect == "postgresql":
        async with engine.connect() as conn:
            await conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')


async def close_db():
    engine = _get_engine()
    await engine.dispose()
