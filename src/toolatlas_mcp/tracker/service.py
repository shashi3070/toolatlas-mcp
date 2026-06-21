import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from toolatlas_mcp.registry.repository import RegistryRepository


class TrackingContext:
    def __init__(self, repo: RegistryRepository):
        self.repo = repo
        self.start_time: float = 0.0
        self.tool_name: str = ""
        self.proxy_id: str | None = None
        self.tool_id: str | None = None
        self.server_id: str | None = None
        self.client_id: str | None = None
        self.request_args: dict | None = None

    async def record_success(self, response_summary: str | None = None):
        duration_ms = (time.time() - self.start_time) * 1000
        await self.repo.record_call(
            tool_name=self.tool_name,
            proxy_id=self.proxy_id,
            tool_id=self.tool_id,
            server_id=self.server_id,
            request_args=self.request_args,
            response_summary=response_summary,
            duration_ms=duration_ms,
            success=True,
            client_id=self.client_id,
        )

    async def record_error(self, error_message: str):
        duration_ms = (time.time() - self.start_time) * 1000
        await self.repo.record_call(
            tool_name=self.tool_name,
            proxy_id=self.proxy_id,
            tool_id=self.tool_id,
            server_id=self.server_id,
            request_args=self.request_args,
            duration_ms=duration_ms,
            success=False,
            error_message=error_message,
            client_id=self.client_id,
        )


class TrackerService:
    def __init__(self, db: AsyncSession):
        self.repo = RegistryRepository(db)

    @asynccontextmanager
    async def track(
        self,
        tool_name: str,
        proxy_id: str | None = None,
        tool_id: str | None = None,
        server_id: str | None = None,
        client_id: str | None = None,
        request_args: dict | None = None,
    ) -> AsyncGenerator[TrackingContext, Any]:
        ctx = TrackingContext(self.repo)
        ctx.start_time = time.time()
        ctx.tool_name = tool_name
        ctx.proxy_id = proxy_id
        ctx.tool_id = tool_id
        ctx.server_id = server_id
        ctx.client_id = client_id
        ctx.request_args = request_args
        try:
            yield ctx
        except Exception as e:
            await ctx.record_error(str(e))
            raise
        else:
            await ctx.record_success()
