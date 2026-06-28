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
from toolatlas_mcp.registry.storage import StorageBackend


def _utcnow():
    return datetime.now(timezone.utc)


def _model_to_dict(model) -> dict:
    if model is None:
        return None
    return {c.key: getattr(model, c.key) for c in model.__table__.columns}


def _ensure_str_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [str(x) for x in v]
    return v


class RegistryRepository(StorageBackend):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def commit(self):
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

    # ---- Servers ----

    async def create_server(self, name: str, transport: str = "sse", command: str | None = None, url: str | None = None) -> dict:
        server = Server(name=name, transport=transport, command=command, url=url)
        self.db.add(server)
        await self.commit()
        return _model_to_dict(server)

    async def list_servers(self) -> list[dict]:
        result = await self.db.execute(select(Server).order_by(Server.name))
        return [_model_to_dict(s) for s in result.scalars().all()]

    async def get_server(self, server_id: str) -> dict | None:
        s = await self.db.get(Server, server_id)
        return _model_to_dict(s)

    async def update_server(self, server_id: str, **kwargs) -> dict | None:
        server = await self.db.get(Server, server_id)
        if not server:
            return None
        for k, v in kwargs.items():
            if hasattr(server, k):
                setattr(server, k, v)
        server.updated_at = _utcnow()
        await self.commit()
        return _model_to_dict(server)

    async def update_server_status(self, server_id: str, connection_status: str | None = None,
                                    latency_ms: float | None = None,
                                    reconnect_count: int | None = None,
                                    last_heartbeat=None) -> dict | None:
        kwargs = {}
        if connection_status is not None:
            kwargs["connection_status"] = connection_status
        if latency_ms is not None:
            kwargs["latency_ms"] = latency_ms
        if reconnect_count is not None:
            kwargs["reconnect_count"] = reconnect_count
        if last_heartbeat is not None:
            kwargs["last_heartbeat"] = last_heartbeat
        return await self.update_server(server_id, **kwargs)

    async def get_server_tool_count(self, server_id: str) -> int:
        from sqlalchemy import func, select
        result = await self.db.execute(
            select(func.count(Tool.id)).where(Tool.server_id == server_id)
        )
        return result.scalar() or 0

    async def delete_server(self, server_id: str) -> bool:
        server = await self.db.get(Server, server_id)
        if not server:
            return False
        await self.db.delete(server)
        await self.commit()
        return True

    # ---- Tools ----

    async def upsert_tool(self, server_id: str, name: str, description: str, input_schema: dict[str, Any], auto_commit: bool = True) -> dict:
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
        if auto_commit:
            await self.commit()
        return _model_to_dict(tool)

    async def list_tools(self, server_id: str | None = None) -> list[dict]:
        stmt = select(Tool).order_by(Tool.server_id, Tool.name)
        if server_id:
            stmt = stmt.where(Tool.server_id == server_id)
        result = await self.db.execute(stmt)
        return [_model_to_dict(t) for t in result.scalars().all()]

    async def get_tool(self, tool_id: str) -> dict | None:
        t = await self.db.get(Tool, tool_id)
        return _model_to_dict(t)

    async def update_tool(self, tool_id: str, **kwargs) -> dict | None:
        tool = await self.db.get(Tool, tool_id)
        if not tool:
            return None
        for k, v in kwargs.items():
            if hasattr(tool, k):
                setattr(tool, k, v)
        tool.updated_at = _utcnow()
        await self.commit()
        return _model_to_dict(tool)

    async def delete_tool(self, tool_id: str) -> bool:
        tool = await self.db.get(Tool, tool_id)
        if not tool:
            return False
        await self.db.delete(tool)
        await self.commit()
        return True

    # ---- Proxies ----

    async def create_proxy(self, name: str, slug: str, description: str = "") -> dict:
        proxy = Proxy(name=name, slug=slug, description=description)
        self.db.add(proxy)
        await self.commit()
        return _model_to_dict(proxy)

    async def list_proxies(self) -> list[dict]:
        result = await self.db.execute(select(Proxy).order_by(Proxy.name))
        return [_model_to_dict(p) for p in result.scalars().all()]

    async def get_proxy(self, proxy_id: str) -> dict | None:
        p = await self.db.get(Proxy, proxy_id)
        return _model_to_dict(p)

    async def get_proxy_by_slug(self, slug: str) -> dict | None:
        result = await self.db.execute(select(Proxy).where(Proxy.slug == slug))
        return _model_to_dict(result.scalar_one_or_none())

    async def update_proxy(self, proxy_id: str, **kwargs) -> dict | None:
        proxy = await self.db.get(Proxy, proxy_id)
        if not proxy:
            return None
        for k, v in kwargs.items():
            if hasattr(proxy, k):
                setattr(proxy, k, v)
        proxy.updated_at = _utcnow()
        await self.commit()
        return _model_to_dict(proxy)

    async def delete_proxy(self, proxy_id: str) -> bool:
        proxy = await self.db.get(Proxy, proxy_id)
        if not proxy:
            return False
        await self.db.delete(proxy)
        await self.commit()
        return True

    # ---- Proxy-Server links ----

    async def link_server_to_proxy(self, proxy_id: str, server_id: str, selected_tools: list[str] | None = None):
        existing = await self.db.execute(
            select(ProxyServer).where(
                ProxyServer.proxy_id == proxy_id, ProxyServer.server_id == server_id
            )
        )
        link = existing.scalar_one_or_none()
        if link:
            if selected_tools is not None:
                link.selected_tools = selected_tools
        else:
            link = ProxyServer(proxy_id=proxy_id, server_id=server_id, selected_tools=selected_tools)
            self.db.add(link)
        await self.commit()

    async def get_proxy_server_selection(self, proxy_id: str, server_id: str) -> list[str] | None:
        result = await self.db.execute(
            select(ProxyServer).where(
                ProxyServer.proxy_id == proxy_id, ProxyServer.server_id == server_id
            )
        )
        link = result.scalar_one_or_none()
        return link.selected_tools if link else None

    async def unlink_server_from_proxy(self, proxy_id: str, server_id: str):
        await self.db.execute(
            delete(ProxyServer).where(
                ProxyServer.proxy_id == proxy_id, ProxyServer.server_id == server_id
            )
        )
        await self.commit()

    async def get_proxy_servers(self, proxy_id: str) -> list[dict]:
        result = await self.db.execute(
            select(Server).join(ProxyServer).where(ProxyServer.proxy_id == proxy_id)
        )
        return [_model_to_dict(s) for s in result.scalars().all()]

    # ---- Proxy-Tool settings ----

    async def get_tool_setting(self, proxy_id: str, tool_id: str) -> dict | None:
        result = await self.db.execute(
            select(ProxyToolSetting).where(
                ProxyToolSetting.proxy_id == proxy_id,
                ProxyToolSetting.tool_id == tool_id,
            )
        )
        return _model_to_dict(result.scalar_one_or_none())

    async def upsert_tool_setting(
        self, proxy_id: str, tool_id: str,
        enabled: bool | None = None,
        custom_description: str | None = None,
        alias: str | None = None,
        auto_commit: bool = True,
    ) -> dict:
        result = await self.db.execute(
            select(ProxyToolSetting).where(
                ProxyToolSetting.proxy_id == proxy_id,
                ProxyToolSetting.tool_id == tool_id,
            )
        )
        setting = result.scalar_one_or_none()
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
        if auto_commit:
            await self.commit()
        return _model_to_dict(setting)

    # ---- Glossary ----

    async def create_glossary_term(self, domain_id: str, term: str, definition: str = "") -> dict:
        gt = GlossaryTerm(domain_id=domain_id, term=term, definition=definition)
        self.db.add(gt)
        await self.commit()
        return _model_to_dict(gt)

    async def list_glossary_terms(self) -> list[dict]:
        result = await self.db.execute(
            select(GlossaryTerm, Domain.name.label("domain_name"))
            .join(Domain, GlossaryTerm.domain_id == Domain.id, isouter=True)
            .order_by(GlossaryTerm.term)
        )
        terms = []
        for row in result.all():
            gt = _model_to_dict(row.GlossaryTerm)
            gt["domain_name"] = row.domain_name
            terms.append(gt)
        return terms

    async def get_glossary_term(self, term_id: str) -> dict | None:
        result = await self.db.execute(
            select(GlossaryTerm, Domain.name.label("domain_name"))
            .join(Domain, GlossaryTerm.domain_id == Domain.id, isouter=True)
            .where(GlossaryTerm.id == term_id)
        )
        row = result.one_or_none()
        if not row:
            return None
        gt = _model_to_dict(row.GlossaryTerm)
        gt["domain_name"] = row.domain_name
        return gt

    async def update_glossary_term(self, term_id: str, **kwargs) -> dict | None:
        gt = await self.db.get(GlossaryTerm, term_id)
        if not gt:
            return None
        for k, v in kwargs.items():
            if hasattr(gt, k):
                setattr(gt, k, v)
        gt.updated_at = _utcnow()
        await self.commit()
        return _model_to_dict(gt)

    async def delete_glossary_term(self, term_id: str) -> bool:
        gt = await self.db.get(GlossaryTerm, term_id)
        if not gt:
            return False
        await self.db.delete(gt)
        await self.commit()
        return True

    # ---- Domains ----

    async def create_domain(self, name: str, description: str = "") -> dict:
        domain = Domain(name=name, description=description)
        self.db.add(domain)
        await self.commit()
        return _model_to_dict(domain)

    async def list_domains(self) -> list[dict]:
        result = await self.db.execute(select(Domain).order_by(Domain.name))
        return [_model_to_dict(d) for d in result.scalars().all()]

    async def update_domain(self, domain_id: str, **kwargs) -> dict | None:
        domain = await self.db.get(Domain, domain_id)
        if not domain:
            return None
        for k, v in kwargs.items():
            if hasattr(domain, k):
                setattr(domain, k, v)
        await self.commit()
        return _model_to_dict(domain)

    async def delete_domain(self, domain_id: str) -> bool:
        domain = await self.db.get(Domain, domain_id)
        if not domain:
            return False
        await self.db.execute(
            delete(GlossaryTerm).where(GlossaryTerm.domain_id == domain_id)
        )
        await self.db.delete(domain)
        await self.commit()
        return True

    async def bulk_import_glossary(self, data: list[dict]) -> dict:
        created_domains = 0
        created_terms = 0
        for item in data:
            domain_name = item.get("domain")
            if not domain_name:
                continue
            result = await self.db.execute(select(Domain).where(Domain.name == domain_name))
            domain = result.scalar_one_or_none()
            if domain:
                domain_id = domain.id
            else:
                domain = Domain(name=domain_name, description=item.get("description", ""))
                self.db.add(domain)
                await self.commit()
                domain_id = domain.id
                created_domains += 1
            for t in item.get("terms", []):
                if not t.get("term"):
                    continue
                gt = GlossaryTerm(domain_id=domain_id, term=t["term"], definition=t.get("definition", ""))
                self.db.add(gt)
                created_terms += 1
            await self.commit()
        return {"domains_created": created_domains, "terms_created": created_terms}

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
    ) -> dict:
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
        return _model_to_dict(call)

    async def get_call(self, call_id: str) -> dict | None:
        result = await self.db.execute(select(ToolCall).where(ToolCall.id == call_id))
        return _model_to_dict(result.scalar_one_or_none())

    async def list_calls(
        self, proxy_id: str | None = None, tool_id: str | None = None,
        limit: int = 100, offset: int = 0,
    ) -> list[dict]:
        stmt = select(ToolCall).order_by(ToolCall.timestamp.desc())
        if proxy_id:
            stmt = stmt.where(ToolCall.proxy_id == proxy_id)
        if tool_id:
            stmt = stmt.where(ToolCall.tool_id == tool_id)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return [_model_to_dict(c) for c in result.scalars().all()]

    async def get_call_stats(self) -> dict[str, Any]:
        from datetime import datetime, timedelta, timezone
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
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
        calls_per_minute = await self.db.execute(
            select(func.count(ToolCall.id))
            .where(ToolCall.timestamp >= cutoff)
        )

        return {
            "total_calls": total.scalar() or 0,
            "successful_calls": successful.scalar() or 0,
            "avg_latency_ms": round(avg_latency.scalar() or 0.0, 2),
            "calls_per_minute": calls_per_minute.scalar() or 0,
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
