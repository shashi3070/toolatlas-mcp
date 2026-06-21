from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from toolatlas_mcp.registry.models import (
    Domain,
    GlossaryTerm,
    Proxy,
    ProxyServer,
    ProxyToolSetting,
    Server,
    Tool,
    ToolCall,
)


def _utcnow():
    return datetime.now(timezone.utc)


class RegistryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def commit(self):
        await self.db.commit()

    # ---- Servers ----

    async def create_server(self, name: str, transport: str = "sse", command: str | None = None, url: str | None = None) -> Server:
        server = Server(name=name, transport=transport, command=command, url=url)
        self.db.add(server)
        await self.commit()
        return server

    async def list_servers(self) -> list[Server]:
        result = await self.db.execute(select(Server).order_by(Server.name))
        return list(result.scalars().all())

    async def get_server(self, server_id: str) -> Server | None:
        return await self.db.get(Server, server_id)

    async def update_server(self, server_id: str, **kwargs) -> Server | None:
        server = await self.get_server(server_id)
        if not server:
            return None
        for k, v in kwargs.items():
            if hasattr(server, k):
                setattr(server, k, v)
        server.updated_at = _utcnow()
        await self.commit()
        return server

    async def delete_server(self, server_id: str) -> bool:
        server = await self.get_server(server_id)
        if not server:
            return False
        await self.db.delete(server)
        await self.commit()
        return True

    # ---- Tools ----

    async def upsert_tool(self, server_id: str, name: str, description: str, input_schema: dict[str, Any]) -> Tool:
        result = await self.db.execute(
            select(Tool).where(Tool.server_id == server_id, Tool.name == name)
        )
        tool = result.scalar_one_or_none()
        if tool:
            if not tool.original_description:
                tool.original_description = description
            if not tool.description or tool.description == tool.original_description:
                tool.description = description
            if input_schema:
                tool.input_schema = input_schema
            tool.updated_at = _utcnow()
        else:
            tool = Tool(
                server_id=server_id,
                name=name,
                original_name=name,
                original_description=description,
                description=description,
                input_schema=input_schema,
            )
            self.db.add(tool)
        await self.commit()
        return tool

    async def list_tools(self, server_id: str | None = None) -> list[Tool]:
        stmt = select(Tool).order_by(Tool.server_id, Tool.name)
        if server_id:
            stmt = stmt.where(Tool.server_id == server_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_tool(self, tool_id: str) -> Tool | None:
        return await self.db.get(Tool, tool_id)

    async def update_tool(self, tool_id: str, **kwargs) -> Tool | None:
        tool = await self.get_tool(tool_id)
        if not tool:
            return None
        for k, v in kwargs.items():
            if hasattr(tool, k):
                setattr(tool, k, v)
        tool.updated_at = _utcnow()
        await self.commit()
        return tool

    async def delete_tool(self, tool_id: str) -> bool:
        tool = await self.get_tool(tool_id)
        if not tool:
            return False
        await self.db.delete(tool)
        await self.commit()
        return True

    # ---- Proxies ----

    async def create_proxy(self, name: str, slug: str, description: str = "") -> Proxy:
        proxy = Proxy(name=name, slug=slug, description=description)
        self.db.add(proxy)
        await self.commit()
        return proxy

    async def list_proxies(self) -> list[Proxy]:
        result = await self.db.execute(select(Proxy).order_by(Proxy.name))
        return list(result.scalars().all())

    async def get_proxy(self, proxy_id: str) -> Proxy | None:
        return await self.db.get(Proxy, proxy_id)

    async def get_proxy_by_slug(self, slug: str) -> Proxy | None:
        result = await self.db.execute(select(Proxy).where(Proxy.slug == slug))
        return result.scalar_one_or_none()

    async def update_proxy(self, proxy_id: str, **kwargs) -> Proxy | None:
        proxy = await self.get_proxy(proxy_id)
        if not proxy:
            return None
        for k, v in kwargs.items():
            if hasattr(proxy, k):
                setattr(proxy, k, v)
        proxy.updated_at = _utcnow()
        await self.commit()
        return proxy

    async def delete_proxy(self, proxy_id: str) -> bool:
        proxy = await self.get_proxy(proxy_id)
        if not proxy:
            return False
        await self.db.delete(proxy)
        await self.commit()
        return True

    # ---- Proxy-Server links ----

    async def link_server_to_proxy(self, proxy_id: str, server_id: str):
        existing = await self.db.execute(
            select(ProxyServer).where(
                ProxyServer.proxy_id == proxy_id, ProxyServer.server_id == server_id
            )
        )
        if not existing.scalar_one_or_none():
            link = ProxyServer(proxy_id=proxy_id, server_id=server_id)
            self.db.add(link)
            await self.commit()

    async def unlink_server_from_proxy(self, proxy_id: str, server_id: str):
        await self.db.execute(
            delete(ProxyServer).where(
                ProxyServer.proxy_id == proxy_id, ProxyServer.server_id == server_id
            )
        )
        await self.commit()

    async def get_proxy_servers(self, proxy_id: str) -> list[Server]:
        result = await self.db.execute(
            select(Server).join(ProxyServer).where(ProxyServer.proxy_id == proxy_id)
        )
        return list(result.scalars().all())

    # ---- Proxy-Tool settings ----

    async def get_tool_setting(self, proxy_id: str, tool_id: str) -> ProxyToolSetting | None:
        result = await self.db.execute(
            select(ProxyToolSetting).where(
                ProxyToolSetting.proxy_id == proxy_id,
                ProxyToolSetting.tool_id == tool_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_tool_setting(
        self, proxy_id: str, tool_id: str,
        enabled: bool | None = None,
        custom_description: str | None = None,
        alias: str | None = None,
    ) -> ProxyToolSetting:
        setting = await self.get_tool_setting(proxy_id, tool_id)
        if setting:
            if enabled is not None:
                setting.enabled = enabled
            if custom_description is not None:
                setting.custom_description = custom_description
            if alias is not None:
                setting.alias = alias
        else:
            setting = ProxyToolSetting(
                proxy_id=proxy_id,
                tool_id=tool_id,
                enabled=enabled if enabled is not None else True,
                custom_description=custom_description,
                alias=alias,
            )
            self.db.add(setting)
        await self.commit()
        return setting

    # ---- Glossary ----

    async def create_glossary_term(self, term: str, definition: str = "") -> GlossaryTerm:
        gt = GlossaryTerm(term=term, definition=definition)
        self.db.add(gt)
        await self.commit()
        return gt

    async def list_glossary_terms(self) -> list[GlossaryTerm]:
        result = await self.db.execute(select(GlossaryTerm).order_by(GlossaryTerm.term))
        return list(result.scalars().all())

    async def get_glossary_term(self, term_id: str) -> GlossaryTerm | None:
        return await self.db.get(GlossaryTerm, term_id)

    async def update_glossary_term(self, term_id: str, **kwargs) -> GlossaryTerm | None:
        gt = await self.get_glossary_term(term_id)
        if not gt:
            return None
        for k, v in kwargs.items():
            if hasattr(gt, k):
                setattr(gt, k, v)
        gt.updated_at = _utcnow()
        await self.commit()
        return gt

    async def delete_glossary_term(self, term_id: str) -> bool:
        gt = await self.get_glossary_term(term_id)
        if not gt:
            return False
        await self.db.delete(gt)
        await self.commit()
        return True

    # ---- Domains ----

    async def create_domain(self, name: str, description: str = "") -> Domain:
        domain = Domain(name=name, description=description)
        self.db.add(domain)
        await self.commit()
        return domain

    async def list_domains(self) -> list[Domain]:
        result = await self.db.execute(select(Domain).order_by(Domain.name))
        return list(result.scalars().all())

    # ---- Tool Calls (tracking) ----

    async def record_call(
        self,
        tool_name: str,
        proxy_id: str | None = None,
        tool_id: str | None = None,
        server_id: str | None = None,
        request_args: dict | None = None,
        response_summary: str | None = None,
        duration_ms: float = 0.0,
        success: bool = True,
        error_message: str | None = None,
        client_id: str | None = None,
        trace_id: str | None = None,
        events: list | None = None,
    ) -> ToolCall:
        call = ToolCall(
            proxy_id=proxy_id,
            tool_id=tool_id,
            server_id=server_id,
            tool_name=tool_name,
            request_args=request_args or {},
            response_summary=response_summary,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            client_id=client_id,
            trace_id=trace_id,
            events=events or [],
        )
        self.db.add(call)
        await self.commit()
        return call

    async def get_call(self, call_id: str) -> ToolCall | None:
        result = await self.db.execute(select(ToolCall).where(ToolCall.id == call_id))
        return result.scalar_one_or_none()

    async def list_calls(
        self, proxy_id: str | None = None, tool_id: str | None = None,
        limit: int = 100, offset: int = 0,
    ) -> list[ToolCall]:
        stmt = select(ToolCall).order_by(ToolCall.timestamp.desc())
        if proxy_id:
            stmt = stmt.where(ToolCall.proxy_id == proxy_id)
        if tool_id:
            stmt = stmt.where(ToolCall.tool_id == tool_id)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_call_stats(self) -> dict[str, Any]:
        from sqlalchemy import func

        total = await self.db.execute(select(func.count(ToolCall.id)))
        successful = await self.db.execute(
            select(func.count(ToolCall.id)).where(ToolCall.success == True)
        )
        avg_latency = await self.db.execute(
            select(func.avg(ToolCall.duration_ms)).where(ToolCall.success == True)
        )
        tool_counts = await self.db.execute(
            select(ToolCall.tool_name, func.count(ToolCall.id).label("count"))
            .group_by(ToolCall.tool_name)
            .order_by(func.count(ToolCall.id).desc())
            .limit(20)
        )

        return {
            "total_calls": total.scalar() or 0,
            "successful_calls": successful.scalar() or 0,
            "avg_latency_ms": round(avg_latency.scalar() or 0.0, 2),
            "top_tools": [{"name": row[0], "calls": row[1]} for row in tool_counts.all()],
        }

    async def get_proxy_stats(self, proxy_id: str) -> dict[str, Any]:
        from sqlalchemy import func

        total = await self.db.execute(
            select(func.count(ToolCall.id)).where(ToolCall.proxy_id == proxy_id)
        )
        successful = await self.db.execute(
            select(func.count(ToolCall.id)).where(
                ToolCall.proxy_id == proxy_id, ToolCall.success == True
            )
        )
        avg_latency = await self.db.execute(
            select(func.avg(ToolCall.duration_ms)).where(
                ToolCall.proxy_id == proxy_id, ToolCall.success == True
            )
        )
        recent = await self.db.execute(
            select(ToolCall)
            .where(ToolCall.proxy_id == proxy_id)
            .order_by(ToolCall.timestamp.desc())
            .limit(20)
        )

        return {
            "total_calls": total.scalar() or 0,
            "successful_calls": successful.scalar() or 0,
            "avg_latency_ms": round(avg_latency.scalar() or 0.0, 2),
            "recent_calls": [
                {
                    "id": c.id,
                    "tool_name": c.tool_name,
                    "duration_ms": c.duration_ms,
                    "success": c.success,
                    "timestamp": c.timestamp.isoformat() if c.timestamp else None,
                }
                for c in recent.scalars().all()
            ],
        }
