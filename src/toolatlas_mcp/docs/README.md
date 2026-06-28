# ToolAtlas MCP Documentation

## Plugin System

| Document | Description |
|----------|-------------|
| [plugin-system.md](plugin-system.md) | Core reference: Plugin base class, hook signatures, hook arguments |
| [plugin-loading.md](plugin-loading.md) | PluginManager API, three loading paths, registration options |
| [plugin-hooks.md](plugin-hooks.md) | Where hooks fire, execution flows, sequence diagrams |
| [plugin-examples.md](plugin-examples.md) | Built-in plugins, AuditLogger, EmailNotifier, scenarios, corner cases |
| [plugin-testing.md](plugin-testing.md) | Testing patterns, mocking, error isolation tests |

## Core System

| Document | Description |
|----------|-------------|
| [proxy-engine.md](proxy-engine.md) | Proxy engine architecture, collision detection, alias system, governance |
| [tool-graph.md](tool-graph.md) | Graph model, call traces, co-occurrence analysis, API endpoints |
| [registry.md](registry.md) | Data layer: storage backends, database models, sync service, MCP client |
| [architecture.md](architecture.md) | System architecture overview |

## API & CLI

| Document | Description |
|----------|-------------|
| [api.md](api.md) | REST API endpoint reference |
| [cli.md](cli.md) | CLI commands reference |
| [configuration.md](configuration.md) | Environment variables and configuration |

## Operations

| Document | Description |
|----------|-------------|
| [deploy-under-subpath.md](deploy-under-subpath.md) | Deploying behind a reverse proxy with URL prefix |
| [troubleshooting.md](troubleshooting.md) | Common issues and solutions |

## Development

| Document | Description |
|----------|-------------|
| [development.md](development.md) | Setup, code layout, testing, contributing |
| [changelog.md](changelog.md) | Version history |

## Examples

See the [examples/](../examples/README.md) directory for runnable example scripts.
