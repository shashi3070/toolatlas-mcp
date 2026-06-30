import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from uuid import uuid4

from toolatlas_mcp.registry.storage import StorageBackend


class ProxyMiddleware:
    def __init__(self, storage: StorageBackend):
        self.storage = storage

    @asynccontextmanager
    async def track(
        self,
        tool_name: str,
        proxy_id: str | None = None,
        tool_id: str | None = None,
        server_id: str | None = None,
        client_id: str | None = None,
        request_args: dict | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
        parent_span_id: str | None = None,
        org_id: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
    ) -> AsyncGenerator[dict, Any]:
        events: list[dict] = []
        trace_id = trace_id or str(uuid4())
        span_id = span_id or str(uuid4())

        def add_event(event_type: str, description: str, details: dict | None = None):
            events.append({
                "type": event_type,
                "description": description,
                "details": details or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        start = time.time()
        error_message: str | None = None
        success = True

        add_event("request_received", f"Tool call request received for '{tool_name}'", {
            "tool_name": tool_name, "args": request_args,
        })

        try:
            yield {"add_event": add_event, "trace_id": trace_id, "span_id": span_id}
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            duration_ms = (time.time() - start) * 1000
            add_event("call_completed", f"Tool call completed in {duration_ms:.0f}ms", {
                "duration_ms": duration_ms, "success": success,
            })
            await self.storage.record_call(
                tool_name=tool_name,
                proxy_id=proxy_id,
                tool_id=tool_id,
                server_id=server_id,
                request_args=request_args,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
                client_id=client_id,
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                org_id=org_id,
                tenant_id=tenant_id,
                user_id=user_id,
                events=events,
            )
