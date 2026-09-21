# Binary Alchemist Cyber Toolkit

二进制炼金术士 · 网安工具箱

A long-term maintained, extensible desktop security analysis platform for Windows,
built around clean architecture, a plugin system and a unified task/result model.

> This project is intended for security learning, CTF practice, lab environments and
> **authorized** security testing only. It does not ship destructive or stealthy
> capabilities. Never use it against systems you do not own or lack permission to test.

## Design goals

- Stable, low-coupling architecture with a strict dependency direction:
  `UI -> Application -> Domain`, `Infrastructure -> Domain`,
  `Modules -> Application / Domain / Infrastructure`.
- New tools are registered through metadata (`ToolDefinition`) and discovered by the
  `ToolRegistry`; adding a tool never requires editing the main window.
- Every long-running operation goes through the `TaskManager`
  (thread pool + cancellation + timeout + progress), never on the GUI thread.
- Every tool returns a unified `ToolResult` (status, summary, data, findings, logs,
  duration, metadata) and reports issues as structured `Finding` objects with an
  explicit fact / heuristic / risk classification.
- Minimal third-party dependencies: `pydantic` for the core models, with
  `PySide6`, `httpx`, `dnspython`, `cryptography`, `pefile` and `psutil` split into
  optional extras so each phase installs only what it needs.
- PyInstaller-ready path resolution (source checkout vs frozen bundle).

## Project status

Phase 0 (skeleton), Phase 1 (core layer), Phase 2 (GUI framework) and Phase 3
(first tool) are complete. Packaging arrives in a later phase; see
[CHANGELOG.md](CHANGELOG.md) and the phase plan in [AGENTS.md](AGENTS.md).

## Available tools

- **IP 信息分析器** (`network.ip_info`): analyze IPv4/IPv6 addresses and CIDR
  networks - version, network/broadcast addresses, netmask, prefix, address
  counts and scope attributes.

## Requirements

- Windows 10/11
- Python 3.13.x

## Getting started

```powershell
# create a virtual environment (Python 3.13)
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1

# install core + development dependencies
python -m pip install -e ".[dev]"

# launch the desktop application
python main.py

# headless core self-check
python main.py --self-test
```

The GUI starts on a dark professional console theme with a left navigation tree,
dashboard statistics, live task/log panels and a settings dialog. Use
`--plugins` to load plugins from the plugins directory at startup.

Useful commands:

```powershell
python scripts\lint.py    # Ruff lint + format check
python -m mypy core       # static type check
python scripts\test.py    # pytest suite
```

## Layout

```text
main.py / app.py        thin entry point + application composition root
core/                   domain models, registry, task manager, config, logging, exporters
ui/                     PySide6 widgets (later phase)
modules/                security tool modules, grouped by category (later phases)
infrastructure/         adapters: network, filesystem, system providers (later phases)
configs/default.json    shipped default configuration
data/                   SQLite database + user config (runtime)
logs/                   app.log / error.log / security.log (runtime)
plugins/                user plugins (plugin.json + main.py)
tests/                  pytest suite, no external-network dependencies
scripts/                lint.py / test.py / build.py
```

## Configuration

Runtime configuration is JSON-based. Shipped defaults live in `configs/default.json`;
user overrides are written to `data/config.json`. Set `CYBERTOOLKIT_HOME` to relocate
the runtime data/logs/plugins directories. No configuration value is hard-coded in
business code, and sensitive values must never be persisted in plain text.

## Logging

All modules use the standard `logging` module through `core.logger`. Three rotating
files are maintained: `logs/app.log` (all levels), `logs/error.log` (ERROR+),
`logs/security.log` (security-relevant events). Log records carry task and tool ids
when available. `print` is forbidden in business code.

## Testing

```powershell
python scripts\test.py
```

Unit tests only exercise localhost and in-memory/temp fixtures; they never depend on
external internet access. Every core module ships with tests.

## License

[MIT](LICENSE)
