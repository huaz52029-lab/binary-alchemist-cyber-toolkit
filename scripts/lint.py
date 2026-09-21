"""Run Ruff lint and format checks against the whole project."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    print("Running Ruff lint...")
    lint_result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."],
        cwd=PROJECT_ROOT,
        check=False,
    )
    print("Running Ruff format check...")
    format_result = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return max(lint_result.returncode, format_result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
