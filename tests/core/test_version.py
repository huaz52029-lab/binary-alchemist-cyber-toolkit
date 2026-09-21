"""Single version source: package metadata must agree with pyproject.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path

from core import APP_VERSION

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_app_version_matches_pyproject() -> None:
    payload = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert payload["project"]["version"] == APP_VERSION


def test_app_version_is_semver_like() -> None:
    major, minor, patch = APP_VERSION.split(".")
    assert major.isdigit()
    assert minor.isdigit()
    assert patch.isdigit()
