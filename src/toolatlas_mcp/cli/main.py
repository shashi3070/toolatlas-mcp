import logging
import os
import socket
import webbrowser
from pathlib import Path

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from toolatlas_mcp.config import settings
from toolatlas_mcp.registry.storage import get_data_dir

app = typer.Typer(
    name="toolatlas",
    help="ToolAtlas — Discover, Govern, and Optimize MCP Tools",
)
console = Console()

REPO = "https://github.com/shashi3070/toolatlas-mcp"


def _port_file() -> Path:
    return get_data_dir() / "port"


def _write_last_port(port: int):
    _port_file().parent.mkdir(parents=True, exist_ok=True)
    _port_file().write_text(str(port))


def _find_free_port(host: str, preferred: int) -> int:
    for port in range(preferred, preferred + 200):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((host, port)) != 0:
                _write_last_port(port)
                return port
    raise RuntimeError(f"No free port found in range {preferred}-{preferred + 199}")


@app.command()
def start(
    host: str = typer.Option(None, help="Host to bind to"),
    port: int = typer.Option(None, help="Port to bind to"),
    storage: str = typer.Option(None, "--storage", help="Storage backend (json/sqlite/postgres)"),
    data_dir: str = typer.Option(None, "--data-dir", help="Data directory for databases and config"),
    database_url: str = typer.Option(None, "--database-url", help="Database connection URL (e.g. postgresql+asyncpg://user:pass@host:5432/dbname)"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
):
    if data_dir:
        os.environ["TOOLATLAS_DATA_DIR"] = data_dir
    elif "TOOLATLAS_DATA_DIR" not in os.environ:
        data_dir = typer.prompt("Data directory", default=str(get_data_dir()))
        os.environ["TOOLATLAS_DATA_DIR"] = data_dir

    if database_url:
        os.environ["TOOLATLAS_DATABASE_URL"] = database_url
        settings.database_url = database_url

    if "TOOLATLAS_STORAGE_TYPE" in os.environ:
        settings.storage_type = os.environ["TOOLATLAS_STORAGE_TYPE"]
    elif storage:
        os.environ["TOOLATLAS_STORAGE_TYPE"] = storage
        settings.storage_type = storage
    else:
        while True:
            val = typer.prompt("Storage type (json/sqlite/postgres)", default="json")
            if val in ("json", "sqlite", "postgres"):
                break
            console.print("[red]Invalid choice. Enter 'json', 'sqlite', or 'postgres'.[/]")
        os.environ["TOOLATLAS_STORAGE_TYPE"] = val
        settings.storage_type = val

    if settings.storage_type == "sqlite":
        if not database_url and "TOOLATLAS_DATABASE_URL" not in os.environ:
            settings.database_url = f"sqlite+aiosqlite:///{get_data_dir() / 'toolatlas.db'}"
    elif settings.storage_type == "postgres":
        if not database_url and "TOOLATLAS_DATABASE_URL" not in os.environ:
            pg_host = typer.prompt("Postgres host", default="localhost")
            pg_port = typer.prompt("Postgres port", default="5432")
            pg_db = typer.prompt("Database name", default="toolatlas")
            pg_user = typer.prompt("Username", default="postgres")
            pg_pass = typer.prompt("Password", hide_input=True, default="")
            settings.database_url = f"postgresql+asyncpg://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
        try:
            import asyncpg  # noqa: F401
        except ImportError:
            console.print("[red]The 'asyncpg' package is required for PostgreSQL. Install with: pip install toolatlas-mcp[postgres][/]")
            raise typer.Exit(code=1)

    host_val = host or settings.host
    if port:
        port_val = port
    elif "TOOLATLAS_PORT" in os.environ:
        port_val = int(os.environ["TOOLATLAS_PORT"])
    else:
        port_val = typer.prompt("Port", default=settings.port, type=int)
    port_val = _find_free_port(host_val, port_val)
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


@app.command()
def docs(
    open_browser: bool = typer.Option(
        False, "--open", "-o", help="Open the documentation in your browser"
    ),
):
    """Show available documentation and examples."""
    here = Path(__file__).resolve().parent.parent

    candidates = [
        ("installed package", here / "docs"),
        ("repo root", here.parent.parent / "docs"),
    ]
    table = Table(title="ToolAtlas Documentation")
    table.add_column("Source", style="cyan")
    table.add_column("Path")
    table.add_column("Available")

    docs_local = None
    examples_local = None

    for label, path in candidates:
        docs_ok = (path).is_dir()
        table.add_row(label, str(path), "[green]Yes[/]" if docs_ok else "[red]No[/]")
        if docs_ok and docs_local is None:
            docs_local = path
            examples_local = path.parent / "examples"

    console.print(table)
    console.print()

    if docs_local:
        console.print(f"[bold]Docs:[/]     {docs_local}")
        if examples_local and examples_local.is_dir():
            console.print(f"[bold]Examples:[/] {examples_local}")
        console.print(f"[bold]Online:[/]  {REPO}/tree/main/docs")
    else:
        console.print(f"[yellow]Docs not found locally. View online:[/]")
        console.print(f"  {REPO}/tree/main/docs")

    if open_browser and docs_local:
        index = docs_local / "README.md"
        if index.is_file():
            webbrowser.open(str(index.resolve()))
        else:
            webbrowser.open(str(docs_local.resolve()))


@app.callback()
def main():
    pass
