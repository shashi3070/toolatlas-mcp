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


class DomainResponse(ResponseModel):
    id: str
    name: str
    description: str
    created_at: datetime | None = None


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
