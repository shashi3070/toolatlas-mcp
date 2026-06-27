from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ServerCreate(BaseModel):
    name: str
    transport: str = "sse"
    command: str | None = None
    url: str | None = None


class ServerUpdate(BaseModel):
    name: str | None = None
    transport: str | None = None
    command: str | None = None
    url: str | None = None
    enabled: bool | None = None


class DiscoverPreviewRequest(BaseModel):
    transport: str = "sse"
    command: str | None = None
    url: str | None = None


class ServerResponse(ResponseModel):
    id: str
    name: str
    transport: str
    command: str | None = None
    url: str | None = None
    enabled: bool
    connection_status: str = "unknown"
    latency_ms: float | None = None
    reconnect_count: int = 0
    last_heartbeat: datetime | None = None
    last_tool_sync: datetime | None = None
    tool_hash: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ToolResponse(ResponseModel):
    id: str
    server_id: str
    name: str
    original_name: str
    original_description: str | None = None
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    enabled: bool
    tags: list[str] = Field(default_factory=list)
    domain: list[str] = Field(default_factory=list)
    glossary_term_ids: list[str] = Field(default_factory=list)

    @field_validator("domain", mode="before")
    @classmethod
    def coerce_domain(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_tags(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v

    @field_validator("glossary_term_ids", mode="before")
    @classmethod
    def coerce_glossary_term_ids(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v
    server_name: str | None = None


class ToolUpdate(BaseModel):
    description: str | None = None
    enabled: bool | None = None
    tags: list[str] | None = None
    domain: list[str] | None = None
    glossary_term_ids: list[str] | None = None


class ProxyCreate(BaseModel):
    name: str
    slug: str
    description: str = ""


class ProxyUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None


class ProxyResponse(ResponseModel):
    id: str
    name: str
    slug: str
    description: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProxyLinkServer(BaseModel):
    server_id: str
    tool_names: list[str] | None = None


class ToolSettingUpdate(BaseModel):
    enabled: bool | None = None
    custom_description: str | None = None
    alias: str | None = None


class GlossaryTermCreate(BaseModel):
    domain_id: str
    term: str
    definition: str = ""


class GlossaryTermUpdate(BaseModel):
    domain_id: str | None = None
    term: str | None = None
    definition: str | None = None


class GlossaryTermResponse(ResponseModel):
    id: str
    domain_id: str = ""
    term: str
    definition: str
    domain_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DomainCreate(BaseModel):
    name: str
    description: str = ""


class DomainUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class DomainResponse(ResponseModel):
    id: str
    name: str
    description: str
    created_at: datetime | None = None


class BulkImportItem(BaseModel):
    domain: str
    description: str = ""
    terms: list[dict[str, str]] = []


class BulkImportRequest(BaseModel):
    items: list[BulkImportItem]


class BulkImportResponse(BaseModel):
    domains_created: int
    terms_created: int


class CallRecordResponse(ResponseModel):
    id: str
    trace_id: str | None = None
    tool_name: str
    proxy_id: str | None = None
    tool_id: str | None = None
    server_id: str | None = None
    request_args: dict[str, Any] | None = None
    response_summary: str | None = None
    duration_ms: float
    success: bool
    error_message: str | None = None
    timestamp: datetime | None = None
    client_id: str | None = None


class CallDetailResponse(CallRecordResponse):
    events: list[dict[str, Any]] | None = None


class CallStatsResponse(BaseModel):
    total_calls: int
    successful_calls: int
    avg_latency_ms: float
    top_tools: list[dict[str, Any]] = Field(default_factory=list)


class ProxyStatsResponse(BaseModel):
    total_calls: int
    successful_calls: int
    avg_latency_ms: float
    recent_calls: list[dict[str, Any]] = Field(default_factory=list)


class ToolTestRequest(BaseModel):
    arguments: dict[str, Any] = {}


class ToolTestResponse(BaseModel):
    name: str
    result: dict | None = None
    error: str | None = None
    duration_ms: float


class DashboardSummaryResponse(BaseModel):
    servers: dict = Field(default_factory=lambda: {"total": 0, "connected": 0, "disconnected": 0, "unknown": 0, "total_tools": 0})
    proxies: dict = Field(default_factory=lambda: {"total": 0})
    tools: dict = Field(default_factory=lambda: {"total": 0})
    calls: dict = Field(default_factory=lambda: {"per_minute": 0, "total": 0})
    latency: dict = Field(default_factory=lambda: {"avg_ms": 0})
    cache: dict = Field(default_factory=lambda: {"hit_rate": 0, "entries": 0})
    recent_alerts: list = Field(default_factory=list)
    recent_activity: list = Field(default_factory=list)


class ProxyDesignerServer(BaseModel):
    server: ServerResponse
    tools: list[dict] = Field(default_factory=list)


class ProxyDesignerResponse(BaseModel):
    proxy: ProxyResponse
    servers: list[ProxyDesignerServer] = Field(default_factory=list)


class ProxyDesignerSave(BaseModel):
    servers: list[dict] = Field(default_factory=list)


class SearchResult(BaseModel):
    servers: list[ServerResponse] = Field(default_factory=list)
    tools: list[ToolResponse] = Field(default_factory=list)
    proxies: list[ProxyResponse] = Field(default_factory=list)
    glossary_terms: list[GlossaryTermResponse] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    type: str
    name: str
    status: str | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class ServerPingResponse(BaseModel):
    id: str
    status: str
    latency_ms: float | None = None
    connection_status: str
    error: str | None = None


# ── Tool Graph ───────────────────────────────────────────────────────────

class TraceNode(BaseModel):
    id: str
    type: str = "call"
    tool_name: str
    duration_ms: float = 0.0
    success: bool = True
    timestamp: str | None = None


class TraceEdge(BaseModel):
    source: str
    target: str
    label: str | None = None
    duration_ms: float | None = None


class TraceGraphResponse(BaseModel):
    trace_id: str
    nodes: list[TraceNode] = Field(default_factory=list)
    edges: list[TraceEdge] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    tool_count: int = 0


class TraceSummary(BaseModel):
    trace_id: str
    tool_count: int
    total_duration_ms: float
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    success_rate: float = 0.0
    tool_names: list[str] = Field(default_factory=list)


class CoOccurrenceNode(BaseModel):
    id: str
    tool_name: str
    call_count: int


class CoOccurrenceEdge(BaseModel):
    source: str
    target: str
    weight: int
    avg_gap_ms: float | None = None


class CoOccurrenceResponse(BaseModel):
    nodes: list[CoOccurrenceNode] = Field(default_factory=list)
    edges: list[CoOccurrenceEdge] = Field(default_factory=list)
