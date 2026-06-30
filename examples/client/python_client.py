"""MCP Client Example

Connects to a ToolAtlas proxy as an MCP client, lists tools, calls a tool.

Demonstrates the _meta protocol for session tracing — all calls sharing the
same trace_id are grouped together in the ToolAtlas UI. Each span_id is
unique per call; parent_span_id can link a call as a child of another.

Uses the MCP Python SDK (mcp). Requires a running ToolAtlas instance.

Usage:
    python examples/client/python_client.py
"""

import asyncio
import logging
import uuid

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def _make_meta(trace_id: str, parent_span_id: str | None = None) -> dict:
    """Build a _meta dict with trace_id, span_id, and optional parent_span_id."""
    return {
        "trace_id": trace_id,
        "span_id": str(uuid.uuid4()),
        "parent_span_id": parent_span_id,
    }


async def main():
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    PROXY_URL = "http://localhost:8000/proxy/dev"

    # Generate a single trace_id for the entire session so all calls are
    # grouped together in the ToolAtlas trace graph.
    session_trace_id = str(uuid.uuid4())
    previous_span_id: str | None = None

    log.info("Connecting to proxy at %s", PROXY_URL)
    async with sse_client(url=PROXY_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            log.info("Connected! Server info: %s", await session.get_server_info())

            # List tools
            tools = await session.list_tools()
            log.info("Available tools (%d):", len(tools.tools))
            for t in tools.tools:
                log.info("  - %s: %s", t.name, t.description[:80])

            # Call a tool — pass _meta for tracing
            if tools.tools:
                tool = tools.tools[0]
                log.info("Calling tool: %s", tool.name)

                meta = _make_meta(session_trace_id, parent_span_id=previous_span_id)
                result = await session.call_tool(tool.name, {}, _meta=meta)
                log.info("Result: %s", result.content)

                # Store the span_id so we can chain the next call as a child
                previous_span_id = meta["span_id"]

                # Second call — linked as child of the first via parent_span_id
                if len(tools.tools) > 1:
                    tool2 = tools.tools[1]
                    log.info("Calling tool (chained): %s", tool2.name)
                    meta2 = _make_meta(session_trace_id, parent_span_id=previous_span_id)
                    result2 = await session.call_tool(tool2.name, {}, _meta=meta2)
                    log.info("Result: %s", result2.content)

    log.info("Client example completed")


if __name__ == "__main__":
    asyncio.run(main())
