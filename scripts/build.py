"""Build entry point for PyInstaller packaging.

Packaging (onedir first, then installer) is scheduled for a later phase, once the
GUI layer is stable. For now this script only performs an environment preflight so
that the build tooling can be wired into CI early.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 13)


def _preflight() -> list[str]:
    problems: list[str] = []
    version = sys.version_info[:2]
    if version < MIN_PYTHON:
        problems.append(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required, found {sys.version}")
    if platform.system() != "Windows":
        problems.append("PyInstaller builds are currently only supported on Windows.")
    return problems


def main() -> int:
    problems = _preflight()
    if problems:
        for problem in problems:
            print(f"preflight failed: {problem}")
        return 1
    print("Environment preflight passed.")
    print(
        "PyInstaller packaging is not enabled yet: the GUI layer must be stable first. "
        "This will become the `--onedir` build command in a later phase."
    )
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--version"],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
