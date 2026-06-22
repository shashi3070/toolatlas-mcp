# Deploying ToolAtlas Under a Subpath (e.g. `/toolatlas`)

## Goal

Serve ToolAtlas under a URL prefix like `https://xyz.com/toolatlas/...` so that:

- The web dashboard is accessible at `https://xyz.com/toolatlas/`
- The REST API is at `https://xyz.com/toolatlas/api/*`
- MCP clients connect via `https://xyz.com/toolatlas/proxy/{slug}/sse`
- The main app (Flask/FastAPI) remains at `https://xyz.com/` unchanged

---

## How Nginx Prefix Stripping Works

The key mechanism: Nginx's `proxy_pass` with a trailing slash **strips** the subpath prefix before forwarding.

```
Browser:  GET https://xyz.com/toolatlas/api/health
                             │
                        Nginx at /toolatlas/
                             │
                     proxy_pass http://127.0.0.1:8081/
                             │
               ┌─────────────┴────────────┐
               │                          │
      path: /api/health           root_path: /toolatlas
               │                          │
         FastAPI route              URL generation (SSE
         matching works             message_url, OpenAPI)
```

So FastAPI routes **stay unchanged** — they still use `/api/...`, `/proxy/...`. Only:
- The `root_path` is set so generated URLs include the prefix
- The React frontend knows to prepend `/toolatlas` to its API calls and router

---

## Architecture

```
Nginx (single container, port 80/443)
  │
  ├── / ──────────────────► Flask App (gunicorn, port 5000)
  │
  └── /toolatlas/* ───────► ToolAtlas FastAPI (uvicorn, port 8081)
           │                    │
           │  Nginx strips      │  FastAPI sees:
           │  /toolatlas        │
           │                    ├── /api/*              → REST API
           │                    ├── /proxy/{slug}/sse   → SSE (MCP clients)
           │                    ├── /proxy/{slug}/msg   → JSON-RPC
           │                    └── / (SPA fallback)    → React dashboard
           │
           └── Browser/Client uses full paths with /toolatlas/ prefix
```

---

## Changes Required

### Understanding: What Does and Doesn't Change

| Aspect | With `base_path=""` (default) | With `base_path="/toolatlas"` |
|--------|------------------------------|-------------------------------|
| FastAPI routes | `/api/*`, `/proxy/*` | Same (Nginx strips prefix) |
| StaticFiles mount | `/` with `html=True` | Same (Nginx strips prefix) |
| `root_path` on FastAPI | `""` (not set) | `/toolatlas` |
| SSE `message_url` | `/proxy/dev/message/{id}` | `/toolatlas/proxy/dev/message/{id}` |
| React API baseURL | `/api` | `/toolatlas/api` |
| React Router basename | `""` | `/toolatlas` |
| Vite build base | `./` (relative) | `/toolatlas/` (absolute) |

### Files to Modify

#### 1. `src/toolatlas_mcp/config.py` — Add `base_path` setting

```python
class Settings(BaseSettings):
    model_config = {"env_prefix": "TOOLATLAS_"}
    host: str = "127.0.0.1"
    port: int = 8081
    database_url: str = f"sqlite+aiosqlite:///{get_data_dir() / 'toolatlas.db'}"
    storage_type: str = "json"
    log_level: str = "INFO"
    ui_dir: str = ""
    base_path: str = ""  # NEW: e.g. "/toolatlas"
```

#### 2. `src/toolatlas_mcp/api/app.py` — Set `root_path` from settings

What changes:
- Read `settings.base_path` inside `create_app()`
- Pass `root_path=base_path` to `FastAPI()`
- Everything else (routes, static mount) **stays the same**

```python
def create_app() -> FastAPI:
    base_path = settings.base_path
    app = FastAPI(
        title="ToolAtlas-MCP",
        version=__version__,
        root_path=base_path,   # NEW
    )
    # ... middleware, routers, static mount all UNCHANGED ...
```

#### 3. `src/toolatlas_mcp/proxy/server.py` — Fix SSE message URL

The SSE endpoint sends a `message_url` back to the MCP client. It must include the `root_path` so the client posts to the correct path.

```python
@router.get("/proxy/{slug}/sse")
async def proxy_sse(slug: str, request: Request):
    session_id = str(uuid.uuid4())
    base = request.app.root_path or ""    # NEW
    message_url = f"{base}/proxy/{slug}/message/{session_id}"  # was: f"/proxy/{slug}/message/{session_id}"
    # ... rest unchanged ...
```

#### 4. `src/toolatlas_mcp/cli/main.py` — No file change needed

The `create_app()` function reads `settings.base_path` directly from the config. Uvicorn calls `create_app()` as a factory with no args. The `root_path` is set inside the FastAPI constructor via settings, not via uvicorn parameters.

The CLI already runs `uvicorn.run(factory=True)` which calls `create_app()`, and `create_app()` now reads `settings.base_path`. So the flow is:

```
TOOLATLAS_BASE_PATH=/toolatlas toolatlas start
  → settings.base_path = "/toolatlas" (loaded from env by pydantic-settings)
  → uvicorn.run("...app:create_app", factory=True)
  → create_app() reads settings.base_path
  → FastAPI(root_path="/toolatlas")
```

#### 5. `ui/vite.config.ts` — Accept `VITE_BASE_URL` and `VITE_BASE_PATH`

```typescript
export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE_URL || "./",
  build: {
    outDir: resolve(__dirname, "../src/toolatlas_mcp/ui/dist"),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8081",
      "/proxy": "http://127.0.0.1:8081",
    },
  },
});
```

**Why `base` matters:** When `VITE_BASE_URL=/toolatlas/`, the built HTML references assets with absolute paths like `/toolatlas/assets/index-abc.js`. The browser fetches these from Nginx, which strips `/toolatlas` and serves from the dist directory.

#### 6. `ui/src/main.tsx` — Use `VITE_BASE_PATH` for Router basename

```typescript
const basePath = import.meta.env.VITE_BASE_PATH || "";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter basename={basePath}>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
```

#### 7. `ui/src/api/client.ts` — Use `VITE_BASE_PATH` for API baseURL

```typescript
const basePath = import.meta.env.VITE_BASE_PATH || "";
const api = axios.create({ baseURL: `${basePath}/api` });
```

---

## Build Commands

### Default (root path — backward compatible)

```bash
cd ui
npm ci && npm run build
```

### Subpath deployment

```bash
cd ui
VITE_BASE_URL=/toolatlas/ VITE_BASE_PATH=/toolatlas npm run build
```

---

## Nginx Configuration

```nginx
server {
    listen 80;
    server_name xyz.com;

    # Main Flask app
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # ToolAtlas — dashboard, API, and SSE proxy
    location /toolatlas/ {
        # Trailing slash strips /toolatlas before forwarding
        proxy_pass http://127.0.0.1:8081/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # SSE requires long timeout (24h)
        proxy_read_timeout 86400s;
    }
}
```

**Key details:**
- `proxy_pass http://127.0.0.1:8081/;` — trailing slash **strips** `/toolatlas` prefix
- `proxy_http_version 1.1;` + `proxy_set_header Upgrade $http_upgrade;` — required for SSE
- `proxy_buffering off;` — required for streaming (SSE)

---

## Container Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install toolatlas-mcp
RUN pip install toolatlas-mcp

# Build the React SPA with subpath
COPY ui/ ./ui/
WORKDIR /app/ui
RUN VITE_BASE_URL=/toolatlas/ VITE_BASE_PATH=/toolatlas npm ci && npm run build

# Copy the built UI into the Python package
RUN cp -r dist/* ../src/toolatlas_mcp/ui/dist/

WORKDIR /app
COPY . .

# Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Start script
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 80
CMD ["/start.sh"]
```

### start.sh

```bash
#!/bin/bash
set -e

# Start Flask app
gunicorn flask_app:app --bind 127.0.0.1:5000 --workers 4 &

# Start ToolAtlas with subpath
TOOLATLAS_BASE_PATH=/toolatlas \
TOOLATLAS_HOST=127.0.0.1 \
TOOLATLAS_PORT=8081 \
toolatlas start &

# Start Nginx
nginx -g "daemon off;"
```

### docker-compose.yml

```yaml
services:
  app:
    build: .
    ports:
      - "80:80"
    volumes:
      - toolatlas-data:/root/.toolatlas

volumes:
  toolatlas-data:
```

---

## Connecting MCP Clients

### Claude Desktop

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dev": {
      "type": "sse",
      "url": "https://xyz.com/toolatlas/proxy/dev/sse"
    }
  }
}
```

### Cursor / VS Code / Any MCP Client

Same format — register an SSE MCP server with the URL above.

### Custom client (Python)

```python
import httpx, uuid

session_id = str(uuid.uuid4())
base = f"https://xyz.com/toolatlas/proxy/dev/message/{session_id}"

with httpx.Client() as client:
    client.post(base, json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "my-agent", "version": "1.0"}}
    })
    client.post(base, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    tools = client.post(base, json={
        "jsonrpc": "2.0", "id": 2, "method": "list_tools"
    }).json()
```

---

## Verification Checklist

| Step | Expected Result |
|------|----------------|
| `curl https://xyz.com/toolatlas/api/health` | `{"status": "ok", "version": "0.1.6"}` |
| Open `https://xyz.com/toolatlas/` in browser | ToolAtlas dashboard loads with correct routing |
| `curl -X POST https://xyz.com/toolatlas/proxy/dev/message/{uuid}` with `list_tools` | Returns tool list from configured MCP servers |
| Claude Desktop connects via `url: https://xyz.com/toolatlas/proxy/dev/sse` | Connection succeeds, tools appear |
| Open `https://xyz.com/` | Flask app loads unaffected |

---

## Rollback

No changes are made to the existing Flask app. To roll back:

1. Remove the `/toolatlas/` location block from nginx config
2. Stop the ToolAtlas uvicorn process
3. Reload nginx: `nginx -s reload`

The main application is untouched.
