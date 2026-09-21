# AGENTS.md - Engineering rules for Binary Alchemist Cyber Toolkit

This file is authoritative for every agent (human or AI) working on this repository.
Read it before changing anything.

## 1. Project identity

- Product: **Binary Alchemist Cyber Toolkit** (二进制炼金术士 · 网安工具箱).
- Purpose: desktop platform for security learning, CTF, labs and **authorized** tests.
- Python 3.13, PySide6/Qt Widgets GUI, Pydantic models, SQLite, JSON config, PyInstaller.
- The project is a product, not a script dump. Stability, maintainability and
  testability outrank feature count.

## 2. Architecture rules (non-negotiable)

- Dependency direction is one-way:
  `UI -> Application -> Domain`;
  `Infrastructure -> Domain`;
  `Modules -> Application / Domain / Infrastructure`.
- Reverse imports (e.g. `core` importing `ui`, a tool importing `MainWindow`) are
  forbidden. `modules/` and `infrastructure/` must never import `ui/`.
- Security tool modules never touch the main window, never modify other tools' data,
  and never depend on concrete Qt widgets.
- If a feature needs a core change, stop and judge: is it an architecture gap, or a
  special case that belongs in an extension / adapter / provider / plugin?
- Never rewrite stable code for one feature. Find the minimal-impact change first.
- No business logic in UI files. No huge files. No hard-coded paths, colors, or tool
  lists. No bare `except Exception` that swallows errors.

## 3. Adding a tool (the only supported way)

1. Create `modules/<category>/<tool_name>/` with a `BaseTool` subclass.
2. Declare metadata via a `ToolDefinition` (`id` must start with `<category>.`).
3. Implement `run(params, context) -> ToolResult`; never block the GUI thread.
4. Use the provided `ExecutionContext` for logging, progress and cancellation.
5. Return findings as `Finding` objects with an explicit
   `FACT` / `HEURISTIC` / `RISK` kind and a correct severity. Never invent certainty.
6. Add pytest coverage (localhost-only for network tests).

The registry generates navigation and tool pages from these definitions; the main
window must never hard-code a tool button.

## 4. Task and result contracts

- Every long-running operation goes through `TaskManager` (thread pool, bounded
  workers). Statuses: `PENDING / RUNNING / COMPLETED / FAILED / CANCELLED / TIMEOUT`.
- Tools return one `ToolResult` shape: status, summary, data, findings, logs,
  duration, metadata. Exports always read from `ToolResult`.
- Errors surface human-readable messages (see `core/exceptions.to_user_message`);
  tracebacks go to the error log, never raw into the UI.
- High entropy != malware. Missing security headers != vulnerability. Distinguish
  observed facts from heuristics and risk notes.

## 5. Logging, config and data

- `logging` via `core.logger`; never `print` in business code.
- Files: `logs/app.log`, `logs/error.log`, `logs/security.log`.
- Config: `configs/default.json` (shipped) overlaid by `data/config.json` (user).
  Never hard-code config values. Never store secrets in plain text.
- SQLite lives under `data/`. Keep the first-phase schema simple and documented;
  introduce an ORM only when the model genuinely needs it.
- Paths come from `core.paths` only (handles frozen PyInstaller bundles).

## 6. Code quality gates (must pass before commit)

```powershell
python scripts\lint.py        # ruff check + format --check
.venv\Scripts\python.exe -m mypy core app.py main.py
python scripts\test.py        # pytest
```

- Full type hints, docstrings on public APIs, ruff-clean, mypy `strict`.
- Tests must not touch external internet; use localhost and tmp fixtures.

## 7. Git workflow

- Commit per stable phase, never one giant unfinished dump.
- Conventional prefixes: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `build:`.
- After each phase: run tests, fix failures, review the diff, then commit.

## 8. Phase plan (strict order)

0. Skeleton (done) - 1. Core (done) - 2. GUI frame (done) - 3. First tool: IP info (done) -
4. Network tools (done) - 5. Encoding & crypto - 6. Web security - 7. File analysis -
8. System security - 9. CTF - 10. Plugins UI - 11. Reports & history -
12. Full test coverage - 13. Performance - 14. PyInstaller onedir, then installer.

Do not jump ahead. A stable core beats early breadth.

## 9. Security boundary

- Authorized/learning use only. No ransomware, persistence, credential theft,
  stealth, spreading or destructive defaults.
- Dual-use capabilities belong in Advanced modules with explicit lab/authorization
  framing. Active network features require an explicit target.
