# Documentation Overhaul Plan

## Scope

Full restructure of the `docs/` directory: split the monolithic `plugin-system.md` into 5 focused
files, create a new `proxy-engine.md` and `tool-graph.md`, write reference docs, and add a
runnable `examples/` directory.

## Target Structure

```
docs/
  README.md                     # Table of contents
  architecture.md               # System architecture overview
  plugin-system.md              # Core reference: base class, hooks, context
  plugin-loading.md             # PluginManager, 3 loading paths, error isolation
  plugin-hooks.md               # Where hooks fire, execution flows, sequence diagrams
  plugin-examples.md            # AuditLogger, EmailNotifier + scenarios + corner cases
  plugin-testing.md             # Test patterns, mocking, error isolation tests
  proxy-engine.md               # Collision, alias, governance, call routing
  tool-graph.md                 # Graph model, traces, co-occurrence
  registry.md                   # (unchanged)
  api.md                        # REST endpoint reference
  cli.md                        # CLI commands reference
  configuration.md              # All env vars, .env format
  deploy-under-subpath.md       # (unchanged)
  troubleshooting.md            # Common issues, FAQ
  development.md                # Setup, code layout, contributing
  changelog.md                  # Version history

examples/
  README.md
  plugins/
    basic_audit_logger.py
    validation_plugin.py
    rate_limiter.py
    cache_custom.py
    error_handling.py
    notification_slack.py
  proxy/
    setup_governance.py
    collision_scenario.py
    enrichment_demo.py
  client/
    python_client.py
    curl_examples.sh
```

## Content Sourcing

- **plugin-*.md**: Split from the existing 1284-line `plugin-system.md` + new content
- **proxy-engine.md**: Written from the `engine.py` source + the alias/collision work done in earlier sessions
- **tool-graph.md**: Written from `api/routes/graph.py`, `proxy/middleware.py`, `tracker/` source
- **api.md**: Generated from `api/routes/*.py`
- **cli.md**: From `cli/main.py`
- **configuration.md**: From `config.py` env vars
- **troubleshooting.md**: Common issues collected from code + experience
- **development.md**: Project setup, code layout, contribution guidelines
- **changelog.md**: Extracted from `README.md` "What's New" sections

## Implementation Order

1. DOCUMENTATION-PLAN.md (this file — reference)
2. Split plugin-system.md → 5 files + new content
3. Write proxy-engine.md
4. Write tool-graph.md
5. Create examples/ directory
6. Write reference docs (api, cli, configuration, troubleshooting, development)
7. Extract changelog.md
8. Write docs/README.md, architecture.md
9. Update root README.md
