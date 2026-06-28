# CLI Reference

The `toolatlas-mcp` CLI is built with [Typer](https://typer.tiangolo.com/).

## Commands

### `start` — Start the ToolAtlas server

```
toolatlas-mcp start [OPTIONS]
```

| Option | Env Var | Description |
|--------|---------|-------------|
| `--host` | `TOOLATLAS_HOST` | Host to bind to (default: `127.0.0.1`) |
| `--port` | `TOOLATLAS_PORT` | Port to bind to (default: `8081`) |
| `--storage` | `TOOLATLAS_STORAGE_TYPE` | Storage backend: `json`, `sqlite`, `postgres` |
| `--data-dir` | `TOOLATLAS_DATA_DIR` | Data directory for databases and config |
| `--database-url` | `TOOLATLAS_DATABASE_URL` | Database connection URL |
| `--reload` | — | Enable auto-reload (development) |

When `--storage` is not provided, the CLI prompts interactively.

#### Examples

```bash
# Start with JSON storage (default)
toolatlas-mcp start

# Start with SQLite
toolatlas-mcp start --storage sqlite

# Start with PostgreSQL
toolatlas-mcp start --storage postgres --database-url "postgresql+asyncpg://user:pass@host:5432/dbname"

# Start on a specific host/port
toolatlas-mcp start --host 0.0.0.0 --port 8080

# Auto-reload for development
toolatlas-mcp start --reload
```

#### Storage Backend Quick Reference

| Backend | Flag | URL Format | Dependencies |
|---------|------|-----------|--------------|
| JSON | `--storage json` | (file-based in data dir) | None |
| SQLite | `--storage sqlite` | `sqlite+aiosqlite:///path` | `aiosqlite` |
| PostgreSQL | `--storage postgres` | `postgresql+asyncpg://user:pass@host/db` | `asyncpg` |

### `--help` — Show help

```
toolatlas-mcp --help
```

### `--version` — Show version (planned)

## Environment Variables

All CLI options can also be set via environment variables with the `TOOLATLAS_` prefix.

| CLI Option | Environment Variable |
|------------|---------------------|
| `--host` | `TOOLATLAS_HOST` |
| `--port` | `TOOLATLAS_PORT` |
| `--storage` | `TOOLATLAS_STORAGE_TYPE` |
| `--data-dir` | `TOOLATLAS_DATA_DIR` |
| `--database-url` | `TOOLATLAS_DATABASE_URL` |

See [configuration.md](configuration.md) for the full list.
