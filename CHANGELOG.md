# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- GUI framework (PySide6 / Qt Widgets).
- Network, web, encoding, crypto, file analysis, system and CTF tool modules.
- Plugin management UI, report center and task history.
- PyInstaller onedir / installer packaging.

## [0.1.0] - 2026-09-21

### Added

- Project skeleton: `pyproject.toml`, `AGENTS.md`, `README.md`, license and changelog.
- Core layer: `AppContext`, `ConfigManager`, `LoggerManager`, exception hierarchy.
- Unified models: `ToolDefinition`, `Finding`, `ToolResult`, `Task`, `TaskResult`, `Target`.
- `ToolRegistry` and `TaskManager` with cancellation, timeout, progress and listeners.
- Export pipeline: JSON / CSV / TXT exporters plus `ExportManager`.
- Plugin discovery and validation skeleton (`PluginLoader`).
- Pytest / Ruff / MyPy configuration and initial core test suite.

