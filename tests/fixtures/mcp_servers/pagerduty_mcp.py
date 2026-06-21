from tests.fixtures.mcp_servers.base_mcp import BaseMockMCPServer, ToolDef

TOOLS = [
    ToolDef(
        name="list_incidents",
        description="List PagerDuty incidents.",
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["triggered", "acknowledged", "resolved"]},
            },
        },
        mock_result={"content": [{"type": "text", "text": "INC-1: Database down (triggered)\nINC-2: API latency (acknowledged)"}], "incidents": 2},
    ),
    ToolDef(
        name="acknowledge_incident",
        description="Acknowledge a PagerDuty incident.",
        input_schema={
            "type": "object",
            "properties": {
                "incident_id": {"type": "string"},
            },
            "required": ["incident_id"],
        },
        mock_result={"content": [{"type": "text", "text": "Incident INC-1 acknowledged"}], "status": "acknowledged"},
    ),
]


class PagerDutyMCPServer(BaseMockMCPServer):
    def __init__(self, port: int = 9005, latency: float = 0.0, error_rate: float = 0.0):
        super().__init__("PagerDuty", port, TOOLS, latency, error_rate)
