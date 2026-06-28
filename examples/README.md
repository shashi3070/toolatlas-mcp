# Examples

This directory contains runnable example scripts showing how to use ToolAtlas.

## Plugin Examples

Each plugin example is a standalone Python file that can be run directly:

```bash
# Run a plugin example
python examples/plugins/basic_audit_logger.py
```

### Available Plugin Examples

| File | Demonstrates |
|------|-------------|
| `plugins/basic_audit_logger.py` | Minimal plugin with `on_before_tool_call` and `on_after_tool_call` hooks |
| `plugins/validation_plugin.py` | Argument validation in `on_before_tool_call` |
| `plugins/rate_limiter.py` | Per-tool rate limiting with in-memory counter |
| `plugins/cache_custom.py` | Custom in-memory cache using `on_before_list_tools` / `on_after_list_tools` |
| `plugins/error_handling.py` | Demonstrates error isolation — a broken plugin doesn't crash the app |
| `plugins/notification_slack.py` | Sends Slack webhook on every tool call |

## Proxy Examples

Proxy examples use the ToolAtlas REST API (via `httpx`) to demonstrate real proxy
governance scenarios. They require a running ToolAtlas instance.

```bash
# Start ToolAtlas first
uvicorn toolatlas_mcp.api.app:app

# Then run an example
python examples/proxy/setup_governance.py
```

### Available Proxy Examples

| File | Demonstrates |
|------|-------------|
| `proxy/setup_governance.py` | Create proxy, link servers, disable risky tools, set aliases |
| `proxy/collision_scenario.py` | Two servers with same-named tools, verify disambiguation |
| `proxy/enrichment_demo.py` | Add glossary terms and domains, verify description enrichment |

## Client Examples

Client examples show how to connect to a ToolAtlas proxy as an MCP client.

```bash
# Requires a running ToolAtlas instance
python examples/client/python_client.py
```

### Available Client Examples

| File | Demonstrates |
|------|-------------|
| `client/python_client.py` | Connect as MCP client, list tools, call a tool |
| `client/curl_examples.sh` | curl commands for common API operations |
