import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from toolatlas_mcp.db import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


class Server(Base):
    __tablename__ = "servers"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False, unique=True)
    transport = Column(String, nullable=False, default="sse")
    command = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    tools = relationship("Tool", back_populates="server", cascade="all, delete-orphan")
    proxy_links = relationship("ProxyServer", back_populates="server", cascade="all, delete-orphan")


class Tool(Base):
    __tablename__ = "tools"

    id = Column(String, primary_key=True, default=_uuid)
    server_id = Column(String, ForeignKey("servers.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    original_description = Column(Text, nullable=True)
    description = Column(Text, default="")
    input_schema = Column(JSON, default=dict)
    enabled = Column(Boolean, default=True)
    tags = Column(JSON, default=list)
    domain = Column(JSON, default=list)
    glossary_term_id = Column(String, ForeignKey("glossary_terms.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    server = relationship("Server", back_populates="tools")
    glossary_term = relationship("GlossaryTerm")
    proxy_settings = relationship("ProxyToolSetting", back_populates="tool", cascade="all, delete-orphan")
    calls = relationship("ToolCall", back_populates="tool", cascade="all, delete-orphan")


class Proxy(Base):
    __tablename__ = "proxies"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False, unique=True)
    slug = Column(String, nullable=False, unique=True)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    server_links = relationship("ProxyServer", back_populates="proxy", cascade="all, delete-orphan")
    tool_settings = relationship("ProxyToolSetting", back_populates="proxy", cascade="all, delete-orphan")


class ProxyServer(Base):
    __tablename__ = "proxy_servers"

    proxy_id = Column(String, ForeignKey("proxies.id", ondelete="CASCADE"), primary_key=True)
    server_id = Column(String, ForeignKey("servers.id", ondelete="CASCADE"), primary_key=True)

    proxy = relationship("Proxy", back_populates="server_links")
    server = relationship("Server", back_populates="proxy_links")


class ProxyToolSetting(Base):
    __tablename__ = "proxy_tool_settings"

    id = Column(String, primary_key=True, default=_uuid)
    proxy_id = Column(String, ForeignKey("proxies.id", ondelete="CASCADE"), nullable=False)
    tool_id = Column(String, ForeignKey("tools.id", ondelete="CASCADE"), nullable=False)
    enabled = Column(Boolean, default=True)
    custom_description = Column(Text, nullable=True)
    alias = Column(String, nullable=True)

    proxy = relationship("Proxy", back_populates="tool_settings")
    tool = relationship("Tool", back_populates="proxy_settings")


class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"

    id = Column(String, primary_key=True, default=_uuid)
    term = Column(String, nullable=False)
    definition = Column(Text, default="")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class Domain(Base):
    __tablename__ = "domains"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=_utcnow)


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(String, primary_key=True, default=_uuid)
    trace_id = Column(String, nullable=True, index=True)
    proxy_id = Column(String, ForeignKey("proxies.id", ondelete="SET NULL"), nullable=True)
    tool_id = Column(String, ForeignKey("tools.id", ondelete="SET NULL"), nullable=True)
    server_id = Column(String, ForeignKey("servers.id", ondelete="SET NULL"), nullable=True)
    tool_name = Column(String, nullable=False)
    request_args = Column(JSON, default=dict)
    response_summary = Column(Text, nullable=True)
    duration_ms = Column(Float, default=0.0)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=_utcnow)
    client_id = Column(String, nullable=True)
    events = Column(JSON, nullable=True)

    tool = relationship("Tool", back_populates="calls")
    proxy_ref = relationship("Proxy")
    server_ref = relationship("Server")
