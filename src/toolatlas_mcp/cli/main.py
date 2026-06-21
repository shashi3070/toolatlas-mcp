import logging

import typer
import uvicorn
from rich.console import Console

from toolatlas_mcp.config import settings

app = typer.Typer(
    name="toolatlas",
    help="ToolAtlas — Discover, Govern, and Optimize MCP Tools",
)
console = Console()


@app.command()
def start(
    host: str = typer.Option(None, help="Host to bind to"),
    port: int = typer.Option(None, help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
):
    host_val = host or settings.host
    port_val = port or settings.port
    console.print(f"[bold green]ToolAtlas-MCP[/] starting on [bold]{host_val}:{port_val}[/]")
    console.print(f"  Web UI: http://{host_val}:{port_val}")
    console.print(f"  API:    http://{host_val}:{port_val}/api/health")
    uvicorn.run(
        "toolatlas_mcp.api.app:create_app",
        host=host_val,
        port=port_val,
        reload=reload,
        factory=True,
        log_level=settings.log_level.lower(),
    )


@app.callback()
def main():
    pass
