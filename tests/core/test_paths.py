"""Runtime path resolution: home override, Unicode and Windows-style names."""

from __future__ import annotations

from pathlib import Path

from core.paths import RuntimePaths


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
