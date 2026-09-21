"""Build entry point: PyInstaller onedir packaging plus a smoke test."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from collections.abc import Sequence
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


def _run_smoke_test() -> int:
    """Launch the frozen executable with the in-app smoke test."""
    exe = PROJECT_ROOT / "dist" / "BinaryAlchemist" / "BinaryAlchemist.exe"
    if not exe.is_file():
        print(f"build smoke test failed: executable not found at {exe}")
        return 1
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    # Keep the build machine's real user data untouched during the smoke test.
    env["CYBERTOOLKIT_HOME"] = str(PROJECT_ROOT / "work" / "smoke_home")
    result = subprocess.run(
        [str(exe), "--smoke-test"],
        cwd=exe.parent,
        env=env,
        check=False,
    )
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build.py",
        description="Build the PyInstaller onedir bundle and smoke-test it.",
    )
    parser.add_argument("--clean", action="store_true", help="clear the PyInstaller cache")
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="build only; do not launch the frozen executable",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    problems = _preflight()
    if problems:
        for problem in problems:
            print(f"preflight failed: {problem}")
        return 1
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        str(PROJECT_ROOT / "BinaryAlchemist.spec"),
    ]
    if args.clean:
        command.append("--clean")
    print("Running PyInstaller onedir build...")
    build_result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if build_result.returncode != 0:
        print("PyInstaller build failed.")
        return build_result.returncode
    if args.skip_smoke:
        return 0
    print("Running build smoke test...")
    return _run_smoke_test()


if __name__ == "__main__":
    raise SystemExit(main())
