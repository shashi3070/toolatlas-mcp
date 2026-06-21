from tests.fixtures.mcp_servers.base_mcp import BaseMockMCPServer, ToolDef

TOOLS = [
    ToolDef(
        name="search_pages",
        description="Search Confluence pages.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search text"},
                "space": {"type": "string", "description": "Space key"},
            },
            "required": ["query"],
        },
        mock_result={"content": [{"type": "text", "text": "Found 5 pages about 'API'"}], "total": 5},
    ),
    ToolDef(
        name="get_page",
        description="Get a Confluence page by ID.",
        input_schema={
            "type": "object",
            "properties": {
                "page_id": {"type": "string"},
            },
            "required": ["page_id"],
        },
        mock_result={"content": [{"type": "text", "text": "# API Documentation\n\nThis page covers..."}], "title": "API Docs"},
    ),
    ToolDef(
        name="create_page",
        description="Create a new Confluence page.",
        input_schema={
            "type": "object",
            "properties": {
                "space": {"type": "string"},
                "title": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["space", "title", "content"],
        },
        mock_result={"content": [{"type": "text", "text": "Created page: API Guide"}], "page_id": "98765"},
    ),
]


class ConfluenceMCPServer(BaseMockMCPServer):
    def __init__(self, port: int = 9003, latency: float = 0.0, error_rate: float = 0.0):
        super().__init__("Confluence", port, TOOLS, latency, error_rate)
