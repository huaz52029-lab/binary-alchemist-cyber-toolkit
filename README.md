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

Phases 0-4 (skeleton, core, GUI framework, first tool and the network module)
are complete. Packaging arrives in a later phase; see
[CHANGELOG.md](CHANGELOG.md) and the phase plan in [AGENTS.md](AGENTS.md).

## Available tools

Network security module (网络安全):

- **IP 信息分析器** (`network.ip_info`): analyze IPv4/IPv6 addresses and CIDR
  networks - version, network/broadcast addresses, netmask, prefix, address
  counts and scope attributes.
- **Ping 测试** (`network.ping`): system ICMP reachability and latency
  statistics (Windows icmp.dll backend).
- **TCP 连接检测** (`network.tcp_connect`): single TCP connect probe with
  OPEN/CLOSED/TIMEOUT/ERROR status.
- **TCP 端口扫描** (`network.tcp_scan`): bounded, cancellable TCP connect scan
  over a single port or a range, with progress and common-service hints.
- **DNS 查询** (`network.dns`): A/AAAA/CNAME/MX/NS/TXT/PTR/SOA records with
  human-readable error translation.
- **网络接口** (`network.interfaces`): local interface addresses, MAC, status,
  MTU and traffic counters.

Cryptography module (密码学):

- **MD5 哈希逆向分析器** (`crypto.md5_reverse`): offline candidate verification,
  local dictionary matching and bounded charset brute-force search for MD5
  hashes; also exposed in the CTF category as MD5 Hash 分析 (`ctf.md5_reverse`).

> MD5 is a one-way hash function. This tool searches user-provided candidate
> spaces for a matching value; it never queries online services, uploads hashes
> or performs online authentication brute-force.

> Network scanning is intended for local machines, lab environments, CTF
> practice, training ranges and **explicitly authorized** testing only. It
> performs TCP connect scans and never ships exploitation, fingerprinting or
> stealth capabilities.

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
