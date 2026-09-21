"""Run the pytest suite against the project, optionally with coverage."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="test.py", description="Run the pytest suite.")
    parser.add_argument(
        "--cov",
        action="store_true",
        help="measure coverage for core, infrastructure and modules",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    command = [sys.executable, "-m", "pytest"]
    if args.cov:
        command += [
            "--cov=core",
            "--cov=infrastructure",
            "--cov=modules",
            "--cov-report=term-missing:skip-covered",
        ]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
