from tests.fixtures.mcp_servers.base_mcp import BaseMockMCPServer, ToolDef

TOOLS = [
    ToolDef(
        name="send_message",
        description="Send a message to a Slack channel.",
        input_schema={
            "type": "object",
            "properties": {
                "channel": {"type": "string"},
                "text": {"type": "string"},
            },
            "required": ["channel", "text"],
        },
        mock_result={"content": [{"type": "text", "text": "Message sent to #general"}], "ts": "1234567890.1234"},
    ),
    ToolDef(
        name="list_channels",
        description="List Slack channels.",
        input_schema={"type": "object", "properties": {}, "required": []},
        mock_result={"content": [{"type": "text", "text": "Channels: #general, #random, #engineering"}], "channels": ["general", "random", "engineering"]},
    ),
    ToolDef(
        name="get_history",
        description="Get message history from a channel.",
        input_schema={
            "type": "object",
            "properties": {
                "channel": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["channel"],
        },
        mock_result={"content": [{"type": "text", "text": "1. Hello\n2. Hi there\n3. Meeting at 3pm"}], "messages": 3},
    ),
]


class SlackMCPServer(BaseMockMCPServer):
    def __init__(self, port: int = 9006, latency: float = 0.0, error_rate: float = 0.0):
        super().__init__("Slack", port, TOOLS, latency, error_rate)
