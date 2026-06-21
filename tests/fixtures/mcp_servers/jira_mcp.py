from tests.fixtures.mcp_servers.base_mcp import BaseMockMCPServer, ToolDef

TOOLS = [
    ToolDef(
        name="search_issues",
        description="Search Jira issues using JQL.",
        input_schema={
            "type": "object",
            "properties": {
                "jql": {"type": "string", "description": "JQL query string"},
                "max_results": {"type": "integer", "description": "Max results"},
            },
            "required": ["jql"],
        },
        mock_result={"content": [{"type": "text", "text": "ISSUE-1: Login broken\nISSUE-2: API timeout"}], "total": 2},
    ),
    ToolDef(
        name="get_issue",
        description="Get details of a specific Jira issue.",
        input_schema={
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "Issue key (e.g. PROJ-123)"},
            },
            "required": ["issue_key"],
        },
        mock_result={"content": [{"type": "text", "text": "Issue: PROJ-123\nStatus: In Progress\nPriority: High"}], "key": "PROJ-123"},
    ),
    ToolDef(
        name="create_issue",
        description="Create a new Jira issue.",
        input_schema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "summary": {"type": "string"},
                "description": {"type": "string"},
                "issuetype": {"type": "string"},
            },
            "required": ["project", "summary", "issuetype"],
        },
        mock_result={"content": [{"type": "text", "text": "Created ISSUE-42"}], "key": "ISSUE-42"},
    ),
]


class JiraMCPServer(BaseMockMCPServer):
    def __init__(self, port: int = 9002, latency: float = 0.0, error_rate: float = 0.0):
        super().__init__("Jira", port, TOOLS, latency, error_rate)
