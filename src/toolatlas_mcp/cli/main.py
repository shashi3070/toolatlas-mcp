import logging
import os
import socket
from pathlib import Path

import click
import typer
import uvicorn
from rich.console import Console

from toolatlas_mcp.config import settings
from toolatlas_mcp.registry.storage import get_data_dir

app = typer.Typer(
    name="toolatlas",
    help="ToolAtlas — Discover, Govern, and Optimize MCP Tools",
)
console = Console()


def _port_file() -> Path:
    return get_data_dir() / "port"


def _read_last_port() -> int | None:
    pf = _port_file()
    if pf.exists():
        try:
            return int(pf.read_text().strip())
        except (ValueError, OSError):
            pass
    return None


def _write_last_port(port: int):
    _port_file().parent.mkdir(parents=True, exist_ok=True)
    _port_file().write_text(str(port))


def _find_free_port(host: str, preferred: int) -> int:
    last = _read_last_port()
    start = last + 1 if last and last >= preferred else preferred
    for port in range(start, start + 200):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((host, port)) != 0:
                _write_last_port(port)
                return port
    raise RuntimeError(f"No free port found in range {start}-{start + 199}")


@app.command()
def start(
    host: str = typer.Option(None, help="Host to bind to"),
    port: int = typer.Option(None, help="Port to bind to"),
    storage: str = typer.Option(None, "--storage", help="Storage backend (json/sqlite)"),
    data_dir: str = typer.Option(None, "--data-dir", help="Data directory for databases and config"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
):
    if data_dir:
        os.environ["TOOLATLAS_DATA_DIR"] = data_dir
    elif "TOOLATLAS_DATA_DIR" not in os.environ:
        data_dir = typer.prompt("Data directory", default=str(get_data_dir()))
        os.environ["TOOLATLAS_DATA_DIR"] = data_dir

    if "TOOLATLAS_STORAGE_TYPE" in os.environ:
        settings.storage_type = os.environ["TOOLATLAS_STORAGE_TYPE"]
    elif storage:
        os.environ["TOOLATLAS_STORAGE_TYPE"] = storage
        settings.storage_type = storage
    else:
        while True:
            val = typer.prompt("Storage type", default="json")
            if val in ("json", "sqlite"):
                break
            console.print("[red]Invalid choice. Enter 'json' or 'sqlite'.[/]")
        os.environ["TOOLATLAS_STORAGE_TYPE"] = val
        settings.storage_type = val
    settings.database_url = f"sqlite+aiosqlite:///{get_data_dir() / 'toolatlas.db'}"
    host_val = host or settings.host
    port_val = port or _find_free_port(host_val, settings.port)
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
