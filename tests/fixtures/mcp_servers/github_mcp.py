from tests.fixtures.mcp_servers.base_mcp import BaseMockMCPServer, ToolDef

TOOLS = [
    ToolDef(
        name="search_code",
        description="Search code in repositories. Returns matching file paths and snippets.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "repo": {"type": "string", "description": "Repository name (optional)"},
            },
            "required": ["query"],
        },
        mock_result={"content": [{"type": "text", "text": "Found 3 results in repo.git"}], "results": 3},
    ),
    ToolDef(
        name="read_file",
        description="Read file contents from a repository.",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to file"},
                "repo": {"type": "string", "description": "Repository name"},
            },
            "required": ["file_path"],
        },
        mock_result={"content": [{"type": "text", "text": "def hello():\n    print('world')"}], "size": 42},
    ),
    ToolDef(
        name="delete_repo",
        description="DANGER: Delete a repository and all its contents.",
        input_schema={
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Repository to delete"},
            },
            "required": ["repo"],
        },
        mock_result={"content": [{"type": "text", "text": "Repository deleted."}], "deleted": True},
    ),
    ToolDef(
        name="list_prs",
        description="List pull requests for a repository.",
        input_schema={
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Repository name"},
                "state": {"type": "string", "enum": ["open", "closed", "all"]},
            },
            "required": ["repo"],
        },
        mock_result={"content": [{"type": "text", "text": "PR #1: Fix bug\nPR #2: Add feature"}], "count": 2},
    ),
]


class GitHubMCPServer(BaseMockMCPServer):
    def __init__(self, port: int = 9001, latency: float = 0.0, error_rate: float = 0.0):
        super().__init__("GitHub", port, TOOLS, latency, error_rate)
