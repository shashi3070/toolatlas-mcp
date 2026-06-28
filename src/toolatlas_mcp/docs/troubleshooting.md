# Troubleshooting

Common issues and their solutions.

## Server Unreachable

```
WARNING Skipping server 'GitHub' (unreachable)
```

**Causes:**
- The MCP server is not running
- Wrong URL or port in the server configuration
- Network firewall blocking the connection
- The server uses a different transport than configured

**Solutions:**
1. Verify the server is running: `curl http://server-url/health`
2. Check the server configuration: `GET /api/servers/{id}`
3. Reconnect: `POST /api/servers/{id}/reconnect`
4. Test connectivity: `POST /api/servers/{id}/ping`

## Tool Not Found in Proxy

```
ValueError: Tool 'search_issues' not found in proxy 'dev'
```

**Causes:**
- The tool name doesn't match any entry in the proxy's `_tool_to_server` map
- The tool was renamed/collision-disambiguated and the client is using the wrong name
- The tool was disabled or deselected for this proxy

**Solutions:**
1. List proxy tools: `GET /api/proxies/{id}/tools` — note the exact `name` field
2. If a collision suffix was added (e.g. `get_info (ServerB)`), use that full name
3. Check if the tool is enabled: look for `"enabled": false` in the tool setting

## Alias Not Taking Effect

If a tool's display name doesn't change after setting an alias:

**Causes:**
- The alias was set to an empty string (`""`) — clears the alias
- The proxy engine's `_tool_to_server` cache hasn't been rebuilt (happens on next `list_tools`)
- The setting was saved but the GET endpoint returned stale data

**Solutions:**
1. Verify the alias was saved: `GET /api/proxies/{id}/tools/{tool_id}`
2. Trigger a cache rebuild by calling the proxy via the MCP protocol
3. Or invalidate the cache: the engine auto-rebuilds when `_tool_to_server` is empty

## Redis Connection Failed

```
WARNING Redis unavailable at redis://localhost:6379/0, falling back to memory-only cache
```

**Causes:**
- Redis server is not running
- Wrong Redis URL in `TOOLATLAS_REDIS_URL`
- Network/firewall blocking port 6379

**Solutions:**
- This is a non-fatal warning. Cache falls back to in-process memory.
- Start Redis: `redis-server`
- Verify connection: `redis-cli ping`

## Plugin Not Loading

```
ERROR Failed to load plugin from my_plugin.plugin.AuditLoggerPlugin: ...
```

**Causes:**
- Module not found (not on `sys.path`)
- Class name mismatch in the dotted path
- `plugin` module-level variable missing
- Import error inside the plugin file

**Solutions:**
1. Verify the plugin file exists and has the right structure (see [plugin-loading.md](plugin-loading.md))
2. Test the import directly: `python -c "from my_plugin.plugin import plugin"`
3. Check that the directory is on `sys.path` or installed with pip
4. Check the plugin has `plugin = MyPlugin()` at module level

## Database Errors

```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: servers
```

**Causes:**
- Database file doesn't exist (first run should auto-create tables)
- Using the wrong database URL
- Schema migration not applied

**Solutions:**
- Tables are auto-created on first run. Ensure write permissions to the data directory.
- For PostgreSQL, ensure the database exists: `CREATE DATABASE toolatlas;`
- If running with `--reload`, ensure the database file path is consistent

## Web UI Shows Empty / Blank

**Causes:**
- The `ui_dir` config is not pointing to the built UI files
- CORS misconfiguration
- Static files not mounted

**Solutions:**
- Check `TOOLATLAS_UI_DIR` points to the built `dist/` directory
- Open browser console for CORS errors
- Verify `http://localhost:8081/` returns the index.html

## Enabling Debug Logging

Set the log level to DEBUG to see detailed plugin execution and engine state:

```bash
export TOOLATLAS_LOG_LEVEL=DEBUG
toolatlas-mcp start
```

## Inspecting Engine State

To see what the proxy engine currently has mapped, make a tool listing request
and watch the server logs. The engine logs every server connection, tool listing,
and collision detection event at DEBUG level.
