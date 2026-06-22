from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from toolatlas_mcp.config import settings
from toolatlas_mcp.registry.storage import StorageBackend, get_data_dir

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
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

        async with async_session_factory() as session:
            yield RegistryRepository(session)


async def init_db():
    async with engine.begin() as conn:
        from toolatlas_mcp.registry.models import Base as RegistryBase
        await conn.run_sync(RegistryBase.metadata.create_all)


async def close_db():
    await engine.dispose()
