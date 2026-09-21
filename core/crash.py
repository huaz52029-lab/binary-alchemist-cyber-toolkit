"""Top-level crash reporting shared by the bootstrap and the GUI runtime."""

from __future__ import annotations

import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path
from types import TracebackType

from core import APP_VERSION
from core.paths import data_root


def crash_log_path() -> Path:
    """Return the crash log location, creating the logs directory as needed."""
    directory = data_root() / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "crash.log"


def write_crash_report(
    exc_type: type[BaseException] | None,
    exc: BaseException | None,
    tb: TracebackType | None,
) -> Path:
    """Persist time/version/OS/runtime metadata plus the traceback.

    Only exception metadata is written; business payloads and user data are
    deliberately kept out of the crash log.
    """
    path = crash_log_path()
    lines = [
        f"time: {datetime.now().isoformat()}",
        f"version: {APP_VERSION}",
        f"os: {platform.platform()}",
        f"python: {sys.version.split()[0]}",
        "",
    ]
    if exc is not None:
        lines.extend(traceback.format_exception(exc_type, exc, tb))
    else:
        lines.append("(no exception object)")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
