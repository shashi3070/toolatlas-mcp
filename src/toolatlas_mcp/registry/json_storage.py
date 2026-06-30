import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from toolatlas_mcp.registry.storage import StorageBackend


def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


def _serialize(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, set):
        return list(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _ensure_str_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [str(x) for x in v]
    return []


class JSONStorage(StorageBackend):
    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._lock = asyncio.Lock()
        self._data: dict[str, list[dict]] = {
            "servers": [],
            "tools": [],
            "proxies": [],
            "proxy_servers": [],
            "proxy_tool_settings": [],
            "glossary_terms": [],
            "domains": [],
            "calls": [],
        }

    async def load(self):
        if self._path.exists():
            raw = self._path.read_text()
            if raw.strip():
                loaded = json.loads(raw)
                for key in self._data:
                    self._data[key] = loaded.get(key, [])

    async def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, default=_serialize, indent=2))

    async def save(self):
        async with self._lock:
            await self._save()

    async def close(self):
        await self.save()

    async def commit(self):
        await self.save()

    def _server_to_dict(self, s: dict) -> dict:
        return {
            "id": s.get("id", ""),
            "name": s.get("name", ""),
            "transport": s.get("transport", "sse"),
            "command": s.get("command"),
            "url": s.get("url"),
            "enabled": s.get("enabled", True),
            "connection_status": s.get("connection_status", "unknown"),
            "latency_ms": s.get("latency_ms"),
            "reconnect_count": s.get("reconnect_count", 0),
            "last_heartbeat": s.get("last_heartbeat"),
            "last_tool_sync": s.get("last_tool_sync"),
            "tool_hash": s.get("tool_hash"),
            "created_at": s.get("created_at"),
            "updated_at": s.get("updated_at"),
        }

    def _tool_to_dict(self, t: dict) -> dict:
        return {
            "id": t.get("id", ""),
            "server_id": t.get("server_id", ""),
            "name": t.get("name", ""),
            "original_name": t.get("original_name", ""),
            "original_description": t.get("original_description"),
            "description": t.get("description", ""),
            "input_schema": t.get("input_schema", {}),
            "enabled": t.get("enabled", True),
            "tags": t.get("tags", []),
            "domain": _ensure_str_list(t.get("domain")),
            "glossary_term_ids": t.get("glossary_term_ids", []),
        }

    # ---- Servers ----

    async def create_server(self, name: str, transport: str = "sse", command: str | None = None, url: str | None = None) -> dict:
        async with self._lock:
            server = {
                "id": _uuid(),
                "name": name,
                "transport": transport,
                "command": command,
                "url": url,
                "enabled": True,
                "connection_status": "unknown",
                "latency_ms": None,
                "reconnect_count": 0,
                "last_heartbeat": None,
                "last_tool_sync": None,
                "tool_hash": None,
                "created_at": _utcnow(),
                "updated_at": _utcnow(),
            }
            self._data["servers"].append(server)
            await self._save()
            return self._server_to_dict(server)

    async def list_servers(self) -> list[dict]:
        return [self._server_to_dict(s) for s in self._data["servers"]]

    async def get_server(self, server_id: str) -> dict | None:
        for s in self._data["servers"]:
            if s["id"] == server_id:
                return self._server_to_dict(s)
        return None

    async def update_server(self, server_id: str, **kwargs) -> dict | None:
        async with self._lock:
            for s in self._data["servers"]:
                if s["id"] == server_id:
                    allowed = ("name", "transport", "command", "url", "enabled",
                               "connection_status", "latency_ms", "reconnect_count",
                               "last_heartbeat", "last_tool_sync", "tool_hash")
                    for k, v in kwargs.items():
                        if v is not None and k in allowed:
                            s[k] = v
                    s["updated_at"] = _utcnow()
                    await self._save()
                    return self._server_to_dict(s)
            return None

    async def update_server_status(self, server_id: str, connection_status: str | None = None,
                                    latency_ms: float | None = None,
                                    reconnect_count: int | None = None,
                                    last_heartbeat=None) -> dict | None:
        return await self.update_server(
            server_id,
            connection_status=connection_status,
            latency_ms=latency_ms,
            reconnect_count=reconnect_count,
            last_heartbeat=last_heartbeat,
        )

    async def get_server_tool_count(self, server_id: str) -> int:
        return sum(1 for t in self._data["tools"] if t["server_id"] == server_id)

    async def delete_server(self, server_id: str) -> bool:
        async with self._lock:
            before = len(self._data["servers"])
            self._data["servers"] = [s for s in self._data["servers"] if s["id"] != server_id]
            deleted_tool_ids = {t["id"] for t in self._data["tools"] if t["server_id"] == server_id}
            self._data["tools"] = [t for t in self._data["tools"] if t["server_id"] != server_id]
            self._data["proxy_servers"] = [
                ps for ps in self._data["proxy_servers"] if ps["server_id"] != server_id
            ]
            self._data["proxy_tool_settings"] = [
                pts for pts in self._data["proxy_tool_settings"]
                if pts["tool_id"] not in deleted_tool_ids
            ]
            if len(self._data["servers"]) < before:
                await self._save()
                return True
            return False

    # ---- Tools ----

    async def upsert_tool(self, server_id: str, name: str, description: str, input_schema: dict[str, Any], auto_commit: bool = True) -> dict:
        async with self._lock:
            for t in self._data["tools"]:
                if t["server_id"] == server_id and t["name"] == name:
                    if not t.get("original_description"):
                        t["original_description"] = description
                    if not t.get("description") or t["description"] == t.get("original_description"):
                        t["description"] = description
                    if input_schema:
                        t["input_schema"] = input_schema
                    t["updated_at"] = _utcnow()
                    if auto_commit:
                        await self._save()
                    return self._tool_to_dict(t)
            tool = {
                "id": _uuid(),
                "server_id": server_id,
                "name": name,
                "original_name": name,
                "original_description": description,
                "description": description,
                "input_schema": input_schema,
                "enabled": True,
                "tags": [],
                "domain": [],
                "glossary_term_ids": [],
                "created_at": _utcnow(),
                "updated_at": _utcnow(),
            }
            self._data["tools"].append(tool)
            if auto_commit:
                await self._save()
            return self._tool_to_dict(tool)

    async def list_tools(self, server_id: str | None = None) -> list[dict]:
        tools = self._data["tools"]
        if server_id:
            tools = [t for t in tools if t["server_id"] == server_id]
        return [self._tool_to_dict(t) for t in tools]

    async def get_tool(self, tool_id: str) -> dict | None:
        for t in self._data["tools"]:
            if t["id"] == tool_id:
                return self._tool_to_dict(t)
        return None

    async def update_tool(self, tool_id: str, **kwargs) -> dict | None:
        async with self._lock:
            for t in self._data["tools"]:
                if t["id"] == tool_id:
                    for k, v in kwargs.items():
                        if v is not None and k in ("description", "enabled", "tags", "domain", "glossary_term_ids"):
                            t[k] = v
                    t["updated_at"] = _utcnow()
                    await self._save()
                    return self._tool_to_dict(t)
            return None

    async def delete_tool(self, tool_id: str) -> bool:
        async with self._lock:
            before = len(self._data["tools"])
            self._data["tools"] = [t for t in self._data["tools"] if t["id"] != tool_id]
            if len(self._data["tools"]) < before:
                await self._save()
                return True
            return False

    # ---- Proxies ----

    async def create_proxy(self, name: str, slug: str, description: str = "") -> dict:
        async with self._lock:
            proxy = {
                "id": _uuid(),
                "name": name,
                "slug": slug,
                "description": description,
                "created_at": _utcnow(),
                "updated_at": _utcnow(),
            }
            self._data["proxies"].append(proxy)
            await self._save()
            return dict(proxy)

    async def list_proxies(self) -> list[dict]:
        return [dict(p) for p in self._data["proxies"]]

    async def get_proxy(self, proxy_id: str) -> dict | None:
        for p in self._data["proxies"]:
            if p["id"] == proxy_id:
                return dict(p)
        return None

    async def get_proxy_by_slug(self, slug: str) -> dict | None:
        for p in self._data["proxies"]:
            if p["slug"] == slug:
                return dict(p)
        return None

    async def update_proxy(self, proxy_id: str, **kwargs) -> dict | None:
        async with self._lock:
            for p in self._data["proxies"]:
                if p["id"] == proxy_id:
                    for k, v in kwargs.items():
                        if v is not None and k in ("name", "slug", "description"):
                            p[k] = v
                    p["updated_at"] = _utcnow()
                    await self._save()
                    return dict(p)
            return None

    async def delete_proxy(self, proxy_id: str) -> bool:
        async with self._lock:
            before = len(self._data["proxies"])
            self._data["proxies"] = [p for p in self._data["proxies"] if p["id"] != proxy_id]
            self._data["proxy_servers"] = [ps for ps in self._data["proxy_servers"] if ps["proxy_id"] != proxy_id]
            if len(self._data["proxies"]) < before:
                await self._save()
                return True
            return False

    # ---- Proxy-Server links ----

    async def link_server_to_proxy(self, proxy_id: str, server_id: str, selected_tools: list[str] | None = None):
        async with self._lock:
            for ps in self._data["proxy_servers"]:
                if ps["proxy_id"] == proxy_id and ps["server_id"] == server_id:
                    if selected_tools is not None:
                        ps["selected_tools"] = selected_tools
                    await self._save()
                    return
            self._data["proxy_servers"].append({
                "proxy_id": proxy_id,
                "server_id": server_id,
                "selected_tools": selected_tools,
            })
            await self._save()

    async def get_proxy_server_selection(self, proxy_id: str, server_id: str) -> list[str] | None:
        for ps in self._data["proxy_servers"]:
            if ps["proxy_id"] == proxy_id and ps["server_id"] == server_id:
                return ps.get("selected_tools")
        return None

    async def unlink_server_from_proxy(self, proxy_id: str, server_id: str):
        async with self._lock:
            self._data["proxy_servers"] = [
                ps for ps in self._data["proxy_servers"]
                if not (ps["proxy_id"] == proxy_id and ps["server_id"] == server_id)
            ]
            await self._save()

    async def get_proxy_servers(self, proxy_id: str) -> list[dict]:
        server_ids = [
            ps["server_id"] for ps in self._data["proxy_servers"]
            if ps["proxy_id"] == proxy_id
        ]
        return [
            self._server_to_dict(s) for s in self._data["servers"]
            if s["id"] in server_ids
        ]

    # ---- Proxy-Tool settings ----

    async def get_tool_setting(self, proxy_id: str, tool_id: str) -> dict | None:
        for ts in self._data["proxy_tool_settings"]:
            if ts["proxy_id"] == proxy_id and ts["tool_id"] == tool_id:
                return dict(ts)
        return None

    async def upsert_tool_setting(self, proxy_id: str, tool_id: str, enabled: bool | None = None, custom_description: str | None = None, alias: str | None = None, auto_commit: bool = True) -> dict:
        async with self._lock:
            for ts in self._data["proxy_tool_settings"]:
                if ts["proxy_id"] == proxy_id and ts["tool_id"] == tool_id:
                    if enabled is not None:
                        ts["enabled"] = enabled
                    if custom_description is not None:
                        ts["custom_description"] = custom_description
                    if alias is not None:
                        ts["alias"] = alias
                    await self._save()
                    return dict(ts)
            setting = {
                "id": _uuid(),
                "proxy_id": proxy_id,
                "tool_id": tool_id,
                "enabled": enabled if enabled is not None else True,
                "custom_description": custom_description,
                "alias": alias,
            }
            self._data["proxy_tool_settings"].append(setting)
            if auto_commit:
                await self._save()
            return dict(setting)

    # ---- Glossary ----

    async def create_glossary_term(self, domain_id: str, term: str, definition: str = "") -> dict:
        async with self._lock:
            gt = {
                "id": _uuid(),
                "domain_id": domain_id,
                "term": term,
                "definition": definition,
                "created_at": _utcnow(),
                "updated_at": _utcnow(),
            }
            self._data["glossary_terms"].append(gt)
            await self._save()
            return dict(gt)

    async def list_glossary_terms(self) -> list[dict]:
        terms = []
        for g in self._data["glossary_terms"]:
            gt = dict(g)
            domain = self._get_domain(gt.get("domain_id", ""))
            gt["domain_name"] = domain.get("name") if domain else None
            terms.append(gt)
        return terms

    async def get_glossary_term(self, term_id: str) -> dict | None:
        for g in self._data["glossary_terms"]:
            if g["id"] == term_id:
                gt = dict(g)
                domain = self._get_domain(gt.get("domain_id", ""))
                gt["domain_name"] = domain.get("name") if domain else None
                return gt
        return None

    async def update_glossary_term(self, term_id: str, **kwargs) -> dict | None:
        async with self._lock:
            for g in self._data["glossary_terms"]:
                if g["id"] == term_id:
                    for k, v in kwargs.items():
                        if v is not None and k in ("domain_id", "term", "definition"):
                            g[k] = v
                    g["updated_at"] = _utcnow()
                    await self._save()
                    return dict(g)
            return None

    async def delete_glossary_term(self, term_id: str) -> bool:
        async with self._lock:
            before = len(self._data["glossary_terms"])
            self._data["glossary_terms"] = [g for g in self._data["glossary_terms"] if g["id"] != term_id]
            if len(self._data["glossary_terms"]) < before:
                await self._save()
                return True
            return False

    def _get_domain(self, domain_id: str) -> dict | None:
        for d in self._data["domains"]:
            if d["id"] == domain_id:
                return dict(d)
        return None

    # ---- Domains ----

    async def create_domain(self, name: str, description: str = "") -> dict:
        async with self._lock:
            domain = {
                "id": _uuid(),
                "name": name,
                "description": description,
                "created_at": _utcnow(),
            }
            self._data["domains"].append(domain)
            await self._save()
            return dict(domain)

    async def list_domains(self) -> list[dict]:
        return [dict(d) for d in self._data["domains"]]

    async def update_domain(self, domain_id: str, **kwargs) -> dict | None:
        async with self._lock:
            for d in self._data["domains"]:
                if d["id"] == domain_id:
                    for k, v in kwargs.items():
                        if v is not None and k in ("name", "description"):
                            d[k] = v
                    await self._save()
                    return dict(d)
            return None

    async def delete_domain(self, domain_id: str) -> bool:
        async with self._lock:
            before = len(self._data["domains"])
            self._data["domains"] = [d for d in self._data["domains"] if d["id"] != domain_id]
            self._data["glossary_terms"] = [g for g in self._data["glossary_terms"] if g.get("domain_id") != domain_id]
            if len(self._data["domains"]) < before:
                await self._save()
                return True
            return False

    async def bulk_import_glossary(self, data: list[dict]) -> dict:
        created_domains = 0
        created_terms = 0
        for item in data:
            domain_name = item.get("domain")
            if not domain_name:
                continue
            existing = [d for d in self._data["domains"] if d["name"] == domain_name]
            if existing:
                domain_id = existing[0]["id"]
            else:
                domain_id = _uuid()
                self._data["domains"].append({
                    "id": domain_id,
                    "name": domain_name,
                    "description": item.get("description", ""),
                    "created_at": _utcnow(),
                })
                created_domains += 1
            for t in item.get("terms", []):
                if not t.get("term"):
                    continue
                self._data["glossary_terms"].append({
                    "id": _uuid(),
                    "domain_id": domain_id,
                    "term": t["term"],
                    "definition": t.get("definition", ""),
                    "created_at": _utcnow(),
                    "updated_at": _utcnow(),
                })
                created_terms += 1
        await self._save()
        return {"domains_created": created_domains, "terms_created": created_terms}

    # ---- Tool Calls ----

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
        span_id: str | None = None,
        parent_span_id: str | None = None,
        org_id: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        events: list | None = None,
    ) -> dict:
        async with self._lock:
            call = {
                "id": _uuid(),
                "trace_id": trace_id,
                "span_id": span_id,
                "parent_span_id": parent_span_id,
                "org_id": org_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "tool_name": tool_name,
                "proxy_id": proxy_id,
                "tool_id": tool_id,
                "server_id": server_id,
                "request_args": request_args or {},
                "response_summary": response_summary,
                "duration_ms": duration_ms,
                "success": success,
                "error_message": error_message,
                "client_id": client_id,
                "events": events or [],
                "timestamp": _utcnow(),
            }
            self._data["calls"].append(call)
            await self._save()
            return dict(call)

    async def get_call(self, call_id: str) -> dict | None:
        for c in self._data["calls"]:
            if c["id"] == call_id:
                return dict(c)
        return None

    async def list_calls(
        self, proxy_id: str | None = None, tool_id: str | None = None,
        org_id: str | None = None, tenant_id: str | None = None,
        limit: int = 100, offset: int = 0,
    ) -> list[dict]:
        calls = sorted(self._data["calls"], key=lambda c: c.get("timestamp", ""), reverse=True)
        if proxy_id:
            calls = [c for c in calls if c.get("proxy_id") == proxy_id]
        if tool_id:
            calls = [c for c in calls if c.get("tool_id") == tool_id]
        if org_id:
            calls = [c for c in calls if c.get("org_id") == org_id]
        if tenant_id:
            calls = [c for c in calls if c.get("tenant_id") == tenant_id]
        return [dict(c) for c in calls[offset:offset + limit]]

    async def get_call_stats(self) -> dict[str, Any]:
        total = len(self._data["calls"])
        successful = sum(1 for c in self._data["calls"] if c.get("success"))
        durations = [c.get("duration_ms", 0) for c in self._data["calls"] if c.get("success")]
        avg_latency = sum(durations) / len(durations) if durations else 0.0
        tool_counts: dict[str, int] = {}
        now = datetime.now(timezone.utc)
        calls_last_minute = 0
        for c in self._data["calls"]:
            ts = c.get("timestamp")
            if ts:
                try:
                    if isinstance(ts, str):
                        ts_dt = datetime.fromisoformat(ts)
                    elif isinstance(ts, datetime):
                        ts_dt = ts
                    else:
                        ts_dt = None
                    if ts_dt and (now - ts_dt).total_seconds() < 60:
                        calls_last_minute += 1
                except (ValueError, TypeError):
                    pass
            name = c.get("tool_name", "unknown")
            tool_counts[name] = tool_counts.get(name, 0) + 1
        top_tools = sorted(tool_counts.items(), key=lambda x: -x[1])[:20]
        return {
            "total_calls": total,
            "successful_calls": successful,
            "avg_latency_ms": round(avg_latency, 2),
            "calls_per_minute": calls_last_minute,
            "top_tools": [{"name": name, "calls": count} for name, count in top_tools],
        }

    async def get_proxy_stats(self, proxy_id: str) -> dict[str, Any]:
        calls = [c for c in self._data["calls"] if c.get("proxy_id") == proxy_id]
        total = len(calls)
        successful = sum(1 for c in calls if c.get("success"))
        durations = [c.get("duration_ms", 0) for c in calls if c.get("success")]
        avg_latency = sum(durations) / len(durations) if durations else 0.0
        recent = sorted(calls, key=lambda c: c.get("timestamp", ""), reverse=True)[:20]
        return {
            "total_calls": total,
            "successful_calls": successful,
            "avg_latency_ms": round(avg_latency, 2),
            "recent_calls": [
                {
                    "id": c.get("id"),
                    "tool_name": c.get("tool_name"),
                    "duration_ms": c.get("duration_ms"),
                    "success": c.get("success"),
                    "timestamp": c.get("timestamp").isoformat() if isinstance(c.get("timestamp"), datetime) else c.get("timestamp"),
                }
                for c in recent
            ],
        }
