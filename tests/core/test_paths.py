"""Runtime path resolution: home override, Unicode and Windows-style names."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from core.paths import RuntimePaths, data_root


def test_resolve_with_chinese_and_space_path(tmp_path: Path) -> None:
    home = tmp_path / "网安 工具箱 测试"
    home.mkdir()
    paths = RuntimePaths.resolve(home)
    assert paths.root == home
    assert paths.data == home / "data"
    paths.ensure_runtime_dirs()
    assert paths.data.is_dir()
    assert paths.logs.is_dir()


def test_default_config_paths_are_derived(tmp_path: Path) -> None:
    paths = RuntimePaths.resolve(tmp_path)
    assert paths.default_config == tmp_path / "configs" / "default.json"
    assert paths.user_config == tmp_path / "data" / "config.json"


def test_frozen_data_root_defaults_to_local_app_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "app" / "BinaryAlchemist.exe"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.delenv("CYBERTOOLKIT_HOME", raising=False)
    assert data_root() == tmp_path / "local" / "BinaryAlchemist"


def test_frozen_portable_flag_keeps_data_next_to_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exe_dir = tmp_path / "app"
    exe_dir.mkdir()
    (exe_dir / "portable.flag").touch()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "BinaryAlchemist.exe"))
    monkeypatch.delenv("CYBERTOOLKIT_HOME", raising=False)
    assert data_root() == exe_dir
