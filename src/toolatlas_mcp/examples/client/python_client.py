"""MCP Client Example

Connects to a ToolAtlas proxy as an MCP client, lists tools, calls a tool.

Uses the MCP Python SDK (mcp). Requires a running ToolAtlas instance.

Usage:
    python examples/client/python_client.py
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


async def main():
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    PROXY_URL = "http://localhost:8000/proxy/dev"

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

            # Call a tool
            if tools.tools:
                tool = tools.tools[0]
                log.info("Calling tool: %s", tool.name)
                result = await session.call_tool(tool.name, {})
                log.info("Result: %s", result.content)

    log.info("Client example completed")


if __name__ == "__main__":
    asyncio.run(main())
