# Bug Fix Plan

## Bug 1 (Critical) — Missing cache invalidation in `update_tool_setting`

**File:** `src/toolatlas_mcp/api/routes/proxies.py:165-184`
**Fix:** Add `invalidate_proxy_cache(proxy["slug"])` after `storage.upsert_tool_setting(...)`.

## Bug 2 (Critical) — Dashboard `calls_per_minute` always 0

**File:** `src/toolatlas_mcp/registry/json_storage.py:566-581`
**File:** `src/toolatlas_mcp/registry/repository.py:456-478`
**Fix:** Compute `calls_per_minute` in both backends' `get_call_stats()`:
- Count calls in the last 60 seconds
- Return as `calls_per_minute`

## Bug 3 (Medium) — JSON storage `delete_server` orphans proxy links

**File:** `src/toolatlas_mcp/registry/json_storage.py:172-180`
**Fix:** After removing the server and its tools, also clean up:
- `proxy_servers` entries referencing this server_id
- `proxy_tool_settings` entries for the deleted tool_ids

## Bug 4 (Medium) — Orphaned engine on proxy slug change / deletion

**File:** `src/toolatlas_mcp/api/routes/proxies.py:50-65` (slug change)
**File:** `src/toolatlas_mcp/api/routes/proxies.py:68-75` (deletion also affected)
**Fix:**
- Add `remove_engine(slug)` function in `server.py`
- Call it in `update_proxy` when slug changes (after cache invalidation)
- Call it in `delete_proxy` to clean up the engine

## Bug 5 (Low) — Redundant commit in `bulk_import_glossary`

**File:** `src/toolatlas_mcp/registry/repository.py:377-401`
**Fix:** Remove the final `await self.commit()` at line 401 (the one inside the loop at line 400 already commits per-item).

## Additional — `on_before_list_tools` never fires

**File:** `src/toolatlas_mcp/proxy/engine.py:59-183`
**Fix:** Fire `on_before_list_tools` at the start of `list_tools()`, before server enumeration. The hook returns `list[dict] | None` — if non-None, short-circuit and return immediately.

## Additional — `on_server_disconnected` never fires

**File:** `src/toolatlas_mcp/services/connection_manager.py:109-116`
**Fix:** Fire `on_server_disconnected` in `_close_client()` before removing the client.
