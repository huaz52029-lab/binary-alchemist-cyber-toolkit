# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Network, web, encoding, crypto, file analysis, system and CTF tool modules.
- Plugin management UI and report center.
- PyInstaller onedir / installer packaging.

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
