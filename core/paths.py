"""Runtime path resolution for the whole application.

All filesystem locations are derived here so that no other module hard-codes paths.
The resolver understands two deployment modes:

* source checkout - paths live under the repository root;
* PyInstaller frozen bundle - user data lives under ``%LOCALAPPDATA%`` unless a
  ``portable.flag`` file sits next to the executable (portable mode).

Set the ``CYBERTOOLKIT_HOME`` environment variable to relocate runtime data
(logs, database, user config and plugins) without touching the code base.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def app_root() -> Path:
    """Return the application root directory."""
    if getattr(sys, "frozen", False):  # pragma: no cover - exercised only when frozen
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    """Return the root for mutable runtime data."""
    override = os.environ.get("CYBERTOOLKIT_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "portable.flag").is_file():
            return exe_dir
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base / "BinaryAlchemist"
    return app_root()


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    """Resolved locations used by the application services."""

    root: Path
    configs: Path
    data: Path
    logs: Path
    plugins: Path
    default_config: Path
    user_config: Path

    @classmethod
    def resolve(cls, home: Path | str | None = None) -> RuntimePaths:
        root = Path(home).expanduser().resolve() if home is not None else data_root()
        return cls(
            root=root,
            configs=root / "configs",
            data=root / "data",
            logs=root / "logs",
            plugins=root / "plugins",
            default_config=root / "configs" / "default.json",
            user_config=root / "data" / "config.json",
        )

    def ensure_runtime_dirs(self) -> None:
        """Create writable runtime directories if they do not exist yet."""
        for directory in (self.data, self.logs):
            directory.mkdir(parents=True, exist_ok=True)
