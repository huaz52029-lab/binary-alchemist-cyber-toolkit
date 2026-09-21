# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Web, encoding, crypto, file analysis, system and CTF tool modules.
- Plugin management UI and report center.
- PyInstaller onedir / installer packaging.

## [0.5.0] - 2026-09-21

### Added

- MD5 哈希逆向分析器 (`crypto.md5_reverse`): offline single/batch candidate
  verification, streaming UTF-8 dictionary matching and bounded charset
  brute-force with progress, speed stats, cancellation and calibrated findings.
- CTF shortcut entry `ctf.md5_reverse` reusing the single implementation.
- Declarative parameter extensions: multiline / file fields, choice labels and
  conditional field visibility; unknown-progress reporting in ExecutionContext.
- `infrastructure/crypto/md5_provider.py` shared MD5 helper.

## [0.4.0] - 2026-09-21

### Added

- Network tool module: Ping, TCP connect check, TCP port scan, DNS query and
  network interfaces, all running through the shared TaskManager / ToolResult /
  exporter pipeline.
- Infrastructure adapters: `TcpClient` (socket), `WindowsPingProvider`
  (icmp.dll), `DnsClient` (dnspython) and `NetworkInterfaceProvider` (psutil).
- Declarative `ToolDefinition.parameters` schema; ToolPage now generates
  parameter forms, plus cancel / progress / row-detail UI features.
- Bounded, cancellable TCP scan with progress reporting and a risk finding for
  large ranges; DNS error translation (NXDOMAIN, timeout, ...); localhost-only
  and mocked network tests.

### Fixed

- icmp.dll echo buffer sizing and payload passing (heap-safe ICMP echo).

## [0.3.0] - 2026-09-21

### Added

- First end-to-end security tool: IP 信息分析器 (`network.ip_info`) covering
  IPv4/IPv6 addresses and CIDR blocks with scope attributes and calibrated
  INFO/FACT findings.
- Tool execution pipeline wiring: ToolPage -> TaskManager -> tool -> ToolResult
  -> ResultPanel, plus copy-to-clipboard and JSON/TXT/CSV export actions.
- Generic grouped key-value view in ResultPanel driven by a tool-provided
  display spec in `ToolResult.metadata`.
- Built-in tool registration through `modules.register_builtin_tools`.
- Unit tests for the analyzer/tool/registry/task manager and offscreen UI
  integration tests for the full chain.

## [0.2.0] - 2026-09-21

### Added

- PySide6 / Qt Widgets GUI framework: main window, navigation, dashboard,
  category and tool pages, task / log / result panels and a settings dialog.
- Dark (default) and light QSS themes managed by a single ThemeManager, plus
  SVG placeholder icons with standard-pixmap fallbacks.
- Qt signal bridges (TaskBridge / LogBridge) connecting TaskManager and
  LoggerManager to the UI without polling.
- Window geometry persistence and startup settings (load plugins on startup).
- Offscreen Qt test suite covering widgets, panels, bridge wiring, theming and
  the main window lifecycle.

### Fixed

- TaskManager PENDING notification could be skipped when a worker raced ahead;
  lifecycle notifications are now emitted before the callable is queued.

## [0.1.0] - 2026-09-21

### Added

- Project skeleton: `pyproject.toml`, `AGENTS.md`, `README.md`, license and changelog.
- Core layer: `AppContext`, `ConfigManager`, `LoggerManager`, exception hierarchy.
- Unified models: `ToolDefinition`, `Finding`, `ToolResult`, `Task`, `TaskResult`, `Target`.
- `ToolRegistry` and `TaskManager` with cancellation, timeout, progress and listeners.
- Export pipeline: JSON / CSV / TXT exporters plus `ExportManager`.
- Plugin discovery and validation skeleton (`PluginLoader`).
- Pytest / Ruff / MyPy configuration and initial core test suite.
