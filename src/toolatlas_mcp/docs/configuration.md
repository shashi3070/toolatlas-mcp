# Configuration

ToolAtlas is configured via environment variables with the `TOOLATLAS_` prefix.
They can be set in a `.env` file in the working directory or exported in the shell.

## Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `TOOLATLAS_HOST` | `127.0.0.1` | Host to bind the HTTP server |
| `TOOLATLAS_PORT` | `8081` | Port to bind the HTTP server |
| `TOOLATLAS_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `TOOLATLAS_BASE_PATH` | `""` | URL sub-path when deployed behind a reverse proxy |

## Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `TOOLATLAS_STORAGE_TYPE` | `json` | Backend: `json`, `sqlite`, or `postgres` |
| `TOOLATLAS_DATABASE_URL` | (derived) | Full database connection URL |
| `TOOLATLAS_DATA_DIR` | (platform-specific) | Directory for data files and databases |

### Database URL formats

| Backend | URL Format |
|---------|-----------|
| SQLite | `sqlite+aiosqlite:////path/to/toolatlas.db` |
| PostgreSQL | `postgresql+asyncpg://user:password@host:5432/dbname` |

### Data Directory

The data directory is determined by platform:

| Platform | Default Path |
|----------|-------------|
| Linux | `~/.local/share/toolatlas-mcp` |
| macOS | `~/Library/Application Support/toolatlas-mcp` |
| Windows | `%APPDATA%/toolatlas-mcp` |

## Cache

| Variable | Default | Description |
|----------|---------|-------------|
| `TOOLATLAS_REDIS_URL` | `""` | Redis connection URL (empty = memory-only cache) |
| `TOOLATLAS_CACHE_TTL` | `300` | Cache TTL in seconds (default 5 minutes) |

Redis URL format: `redis://[[username]:[password]]@localhost:6379/0`

## Registry Sync

| Variable | Default | Description |
|----------|---------|-------------|
| `TOOLATLAS_REGISTRY_SYNC_INTERVAL` | `30` | Background sync interval in seconds |

## Plugin System

| Variable | Default | Description |
|----------|---------|-------------|
| `TOOLATLAS_PLUGINS` | `[]` | Comma-separated list of plugin entry points (planned) |
| `TOOLATLAS_PLUGIN_DIRS` | `[]` | Comma-separated list of plugin scan directories (planned) |

## Example `.env` File

```bash
# Server
TOOLATLAS_HOST=0.0.0.0
TOOLATLAS_PORT=8080
TOOLATLAS_LOG_LEVEL=DEBUG

# Storage
TOOLATLAS_STORAGE_TYPE=sqlite
TOOLATLAS_DATA_DIR=/var/lib/toolatlas

# Cache
TOOLATLAS_REDIS_URL=redis://localhost:6379/0
TOOLATLAS_CACHE_TTL=600

# Registry Sync
TOOLATLAS_REGISTRY_SYNC_INTERVAL=60
```
