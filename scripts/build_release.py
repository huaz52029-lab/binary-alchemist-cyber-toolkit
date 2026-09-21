"""One-command release build for Binary Alchemist Cyber Toolkit.

Order: lint -> typecheck -> pytest -> coverage gate -> PyInstaller ->
smoke test -> portable package -> ZIP -> SHA256 -> release notes -> installer
(Inno Setup, when available).

The version is read from ``pyproject.toml`` so every artifact name and the
version resource come from the single version source.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tomllib
import zipfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "dist" / "BinaryAlchemist"
RELEASE_DIR = PROJECT_ROOT / "release"


def _run(command: list[str], *, label: str) -> int:
    print(f"[build_release] {label}")
    result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if result.returncode != 0:
        print(f"[build_release] FAILED: {label}")
    return result.returncode


def _version() -> str:
    payload = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


def _coverage_gate() -> int:
    print("[build_release] coverage check")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--cov=core",
            "--cov=infrastructure",
            "--cov=modules",
            "--cov-report=json",
        ],
        cwd=PROJECT_ROOT,
        check=False,
    )
    if result.returncode != 0:
        print("[build_release] FAILED: pytest during coverage")
        return result.returncode
    data = json.loads((PROJECT_ROOT / "coverage.json").read_text(encoding="utf-8"))
    totals = data["totals"]
    core_statements = 0
    core_hit = 0
    for path, module in data["files"].items():
        if path.replace("\\", "/").startswith("core/"):
            core_statements += module["summary"]["num_statements"]
            core_hit += module["summary"]["num_statements"] - module["summary"]["missing_lines"]
    core_percent = core_hit / core_statements * 100 if core_statements else 0.0
    total_percent = totals["percent_covered"]
    print(f"[build_release] coverage core={core_percent:.1f}% total={total_percent:.1f}%")
    if core_percent < 90.0 or total_percent < 80.0:
        print("[build_release] FAILED: coverage below gate")
        return 1
    return 0


def _find_iscc() -> Path | None:
    for candidate in (
        PROJECT_ROOT / "work" / "innosetup" / "ISCC.exe",
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ):
        if candidate.is_file():
            return candidate
    return None


def _package_portable(version: str) -> Path:
    folder = RELEASE_DIR / f"BinaryAlchemist-{version}-win64"
    if folder.exists():
        shutil.rmtree(folder)
    shutil.copytree(DIST_DIR, folder)
    (folder / "portable.flag").write_text("portable\n", encoding="utf-8")
    plugins = folder / "plugins"
    plugins.mkdir(exist_ok=True)
    (plugins / "README.txt").write_text(
        "将插件文件夹（含 plugin.json）放到本目录。\n插件与主程序同进程运行，请只安装可信插件。\n",
        encoding="utf-8",
    )
    return folder


def _clean_release_dir() -> None:
    """Remove previously generated artifacts so the release dir is pristine."""
    for entry in RELEASE_DIR.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def _zip_tree(folder: Path) -> Path:
    archive = folder.parent / f"{folder.name}.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                handle.write(path, path.relative_to(folder.parent))
    return archive


def _write_environment(version: str) -> None:
    import PyInstaller
    import PySide6

    lines = [
        f"product: Binary Alchemist Cyber Toolkit {version}",
        f"build date: {datetime.now().isoformat()}",
        f"os: {platform.platform()}",
        f"python: {sys.version.split()[0]}",
        f"pyinstaller: {PyInstaller.__version__}",
        f"pyside6: {PySide6.__version__}",
    ]
    (RELEASE_DIR / "build_environment.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def _write_sha256sums(paths: list[Path]) -> None:
    lines = []
    for path in paths:
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.name}")
    (RELEASE_DIR / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    version = _version()
    print(f"[build_release] version {version}")
    RELEASE_DIR.mkdir(exist_ok=True)
    if _run([sys.executable, "scripts/lint.py"], label="ruff"):
        return 1
    if _run(
        [
            sys.executable,
            "-m",
            "mypy",
            "core",
            "ui",
            "modules",
            "infrastructure",
            "app.py",
            "main.py",
            "scripts",
        ],
        label="mypy",
    ):
        return 1
    if _run([sys.executable, "scripts/test.py"], label="pytest"):
        return 1
    if _coverage_gate():
        return 1
    for directory in ("build", "dist"):
        target = PROJECT_ROOT / directory
        if target.exists():
            shutil.rmtree(target)
    if _run(
        [sys.executable, "scripts/build.py", "--skip-smoke"],
        label="pyinstaller",
    ):
        return 1
    smoke_env = os.environ.copy()
    smoke_env.setdefault("QT_QPA_PLATFORM", "offscreen")
    smoke_env["CYBERTOOLKIT_HOME"] = str(PROJECT_ROOT / "work" / "release_smoke_home")
    smoke = subprocess.run(
        [str(DIST_DIR / "BinaryAlchemist.exe"), "--smoke-test"],
        cwd=DIST_DIR,
        env=smoke_env,
        check=False,
    )
    if smoke.returncode != 0:
        print("[build_release] FAILED: frozen smoke test")
        return 1

    _clean_release_dir()
    folder = _package_portable(version)
    archive = _zip_tree(folder)
    artifacts = [archive]
    print(f"[build_release] portable folder: {folder}")
    print(f"[build_release] portable zip: {archive}")

    iscc = _find_iscc()
    if iscc is None:
        print(
            "[build_release] 未检测到Inno Setup，跳过Installer构建。"
            "安装 Inno Setup 6 后运行：ISCC.exe installer\\BinaryAlchemist.iss"
        )
    else:
        if _run(
            [str(iscc), str(PROJECT_ROOT / "installer" / "BinaryAlchemist.iss")],
            label="inno setup",
        ):
            print("[build_release] FAILED: installer build")
            return 1
        setup = RELEASE_DIR / f"BinaryAlchemist-{version}-Setup.exe"
        if setup.is_file():
            artifacts.append(setup)

    _write_environment(version)
    _write_sha256sums(artifacts)
    release_notes = PROJECT_ROOT / "docs" / "release_notes.md"
    if release_notes.is_file():
        shutil.copyfile(release_notes, RELEASE_DIR / "RELEASE_NOTES.md")
    print("[build_release] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
