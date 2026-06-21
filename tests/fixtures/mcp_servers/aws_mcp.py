from tests.fixtures.mcp_servers.base_mcp import BaseMockMCPServer, ToolDef

TOOLS = [
    ToolDef(
        name="list_s3_buckets",
        description="List all S3 buckets.",
        input_schema={"type": "object", "properties": {}, "required": []},
        mock_result={"content": [{"type": "text", "text": "Buckets: prod-data, dev-assets, logs"}], "buckets": ["prod-data", "dev-assets", "logs"]},
    ),
    ToolDef(
        name="describe_ec2",
        description="Describe EC2 instances.",
        input_schema={
            "type": "object",
            "properties": {
                "instance_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
        mock_result={"content": [{"type": "text", "text": "i-123: running (t3.medium)\ni-456: stopped (t2.micro)"}], "instances": 2},
    ),
    ToolDef(
        name="list_lambdas",
        description="List Lambda functions.",
        input_schema={"type": "object", "properties": {}, "required": []},
        mock_result={"content": [{"type": "text", "text": "Functions: process-orders, send-email"}], "functions": ["process-orders", "send-email"]},
    ),
]


class AWSMCPServer(BaseMockMCPServer):
    def __init__(self, port: int = 9004, latency: float = 0.0, error_rate: float = 0.0):
        super().__init__("AWS", port, TOOLS, latency, error_rate)
