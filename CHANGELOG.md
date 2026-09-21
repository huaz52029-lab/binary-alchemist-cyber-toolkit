# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Installer packaging and reports/history UX refinements.

## [0.14.0] - 2026-09-21

### Added

- Performance benchmarking harness (`scripts/bench.py`), performance baseline
  and report docs, and database maintenance (orphan artifacts, broken report
  references - report first, clean on request) with an ArtifactManager.
- Settings UI for the global task concurrency limit and data maintenance.
- Documentation suite: architecture, development, user guide, configuration
  and third-party licenses.

### Changed

- Frozen releases store user data under `%LOCALAPPDATA%\BinaryAlchemist`;
  a `portable.flag` next to the executable keeps the portable layout.
- TCP scan progress updates are batched (every 100 probes plus a final 100%).
- File entropy counting uses `collections.Counter` (measured ~15-20% faster).
- PyInstaller bundle excludes dev tools (mypy/setuptools) and unused Qt
  modules (QML/Quick/PDF/VirtualKeyboard): ~138MB -> ~116MB.

### Fixed

- TaskPanel row-index shift when inserting new tasks at the top (updates could
  overwrite the wrong row).

## [0.13.0] - 2026-09-21

### Added

- Full-project quality pass: integration tests (localhost HTTP/TCP fixtures,
  registry -> TaskManager -> tool -> history -> exporter chains), regression
  tests (task lifecycle races, CSV injection, path escapes, template paths)
  and stress tests (1000-task bursts, 500-tool registry, SQLite concurrent
  writers, 10k history rows, 10-plugin roundtrips, 100 reports, 100MB
  streaming files).
- Coverage tooling (`scripts/test.py --cov`, targets: core >= 90%, overall
  >= 80% business code) and a GitHub Actions CI workflow (Ruff + MyPy +
  pytest).
- PyInstaller onedir packaging (`BinaryAlchemist.spec`, `scripts/build.py`):
  frozen GUI smoke test entry point (`--smoke-test`), clean-room bundle
  verification and environment-PATH DLL filtering.
- Quality and known-issue reports in `docs/`.

### Fixed

- CSV export formula-injection guard; JSON/TXT/CSV exporters now redact
  sensitive values with the unified sanitizer.
- Corrupt user config no longer blocks startup (quarantine + defaults
  restore); corrupt SQLite database is quarantined and recreated.
- Report templates resolve from the runtime root, fixing frozen-bundle
  template lookup.
- Regex tool rejects high-complexity patterns on large inputs to avoid
  catastrophic backtracking.
- Window geometry restore drops off-screen positions; log bridge detaches on
  window close (no deleted-signal logging crash); self-test shuts down its
  context (no leaked SQLite connections).
- Unified version source: package metadata agrees with `pyproject.toml`
  (0.13.0).

## [0.12.0] - 2026-09-21

### Added

- Task history: SQLite persistence with migrations, pagination, filters,
  search, sorting, deletion (report-reference guarded), artifact spillover for
  large results and startup recovery of interrupted tasks.
- Report center: templates, task references with sections, Markdown renderer,
  JSON/Markdown/TXT export, finding ordering and automatic summaries.
- Unified SensitiveDataSanitizer and per-tool input persistence policy.
- Task history and report center GUI pages plus dashboard recent tasks/reports.

## [0.11.0] - 2026-09-21

### Added

- Plugin system: Plugin SDK (PluginDefinition, PluginContext, PluginConfigManager,
  namespaced tools), isolated PluginLoader, lifecycle PluginManager with
  enable/disable persistence, API-version and dependency checks.
- Plugin management GUI page, bundled example plugin, development template and
  `scripts/create_plugin.py` scaffolding; `docs/plugin_api.md`.

## [0.10.0] - 2026-09-21

### Added

- CTF workbench: enhanced multi-layer Auto Decode (new decoders, chains, depth
  and cycle limits), regex tester with templates, flag extraction, text
  analysis, crypto helper orchestration, modular math, data transform,
  challenge analyzer with tool recommendations.
- Local challenge workspaces (metadata/attachments/notes/results), Markdown
  notes, and versioned local-tool pipelines (active network tools rejected).
- Tool Input Bridge: send results from one tool to another via a unified
  "发送到" menu.

## [0.9.0] - 2026-09-21

### Added

- System security module: system info, processes, process detail, connections,
  Windows services, startup entries, users, environment (sensitive-value
  redaction), resource monitoring and a composite system analyzer with partial
  success.
- Read-only system providers (psutil + pywin32 + winreg KEY_READ): per-field
  access-denied degradation, sensitive-value masking and no mutation
  capabilities whatsoever.

## [0.8.0] - 2026-09-21

### Added

- File analysis module: file info/type detection, single-pass multi-hash,
  streaming strings (ASCII/UTF-8/UTF-16LE), Shannon entropy (file + PE
  sections), paged read-only hex viewer with search, PE analysis (headers,
  sections, imports, exports, resources, overlay), candidate IOC extraction,
  composite analyzer and bounded batch analysis.
- Infrastructure filesystem adapters (streaming reader, magic-byte detector)
  and multi-digest streaming hashing.
- File drag-and-drop on tool pages (path only, never executed).
- Strict static-analysis boundary: no sample execution, no uploads; findings
  are calibrated facts/heuristics.

## [0.7.0] - 2026-09-21

### Added

- Web security module: URL parser, HTTP header analyzer (HEAD + GET fallback),
  Cookie attribute analysis, nine security-header checks, TLS/certificate
  inspection and a composite HTTP analysis tool with page metadata.
- Unified `HttpClient` (httpx GET/HEAD: timeouts, redirect chain tracking,
  bounded response body, cancellation, TLS verification) and `TlsClient`
  (stdlib ssl + cryptography certificate parsing; never bypasses verification).
- Sensitive header redaction (Authorization/Cookie -> [REDACTED]), masked cookie
  values, private-target notices and calibrated findings (missing headers and
  cookie attributes are facts, not vulnerability verdicts).
- Local HTTP/TLS server test fixtures; no external network in tests.

## [0.6.0] - 2026-09-21

### Added

- Encoding module (10 tools): Base64, Base32, Base58 (pure Python), Hex, Binary,
  URL, Unicode escape, ROT13, ROT47 and HTML Entity, sharing one EncodingTool
  base and one EncodingToolPage workspace (encode/decode, copy, swap, clear).
- Crypto tools: Hash calculator (text/file, chunked, compare), XOR (single-byte,
  scored brute-force, repeating-key, hex XOR), JWT decoder/analyzer and RSA
  parameter/PEM helper.
- CTF Auto Decode: heuristic multi-encoding candidates with confidence levels.
- Declarative ``page`` hint on ToolDefinition and shared Base64URL helpers.
- Offline-only behavior: no network calls, no secret logging; calibrated
  findings distinguish facts from heuristics.

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
