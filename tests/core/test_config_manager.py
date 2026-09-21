from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from core.config_manager import AppConfig, ConfigManager

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_shipped_defaults_match_code_defaults() -> None:
    payload = (REPO_ROOT / "configs" / "default.json").read_text(encoding="utf-8")
    assert AppConfig.model_validate_json(payload) == AppConfig()


def test_load_creates_user_config_when_missing(tmp_home: Path) -> None:
    user_path = tmp_home / "data" / "config.json"
    config = ConfigManager(user_path).load()
    assert config == AppConfig()
    assert user_path.exists()


def test_user_overrides_merge_over_defaults(tmp_home: Path) -> None:
    defaults_path = tmp_home / "defaults.json"
    defaults_path.write_text(
        json.dumps({"theme": "dark", "tasks": {"max_workers": 2, "default_timeout": 5.0}}),
        encoding="utf-8",
    )
    user_path = tmp_home / "config.json"
    user_path.write_text(
        json.dumps({"theme": "light", "tasks": {"max_workers": 4}}),
        encoding="utf-8",
    )
    config = ConfigManager(user_path, defaults_path=defaults_path).load()
    assert config.theme == "light"
    assert config.tasks.max_workers == 4
    assert config.tasks.default_timeout == 5.0


def test_unknown_keys_are_warned_and_ignored(
    tmp_home: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user_path = tmp_home / "config.json"
    user_path.write_text(
        json.dumps({"nonsense": 1, "window": {"bogus": 2}}),
        encoding="utf-8",
    )
    with caplog.at_level(logging.WARNING):
        config = ConfigManager(user_path).load()
    assert config.window.width == 1280
    assert "nonsense" in caplog.text
    assert "bogus" in caplog.text


def test_save_and_reload_roundtrip(tmp_home: Path) -> None:
    user_path = tmp_home / "config.json"
    manager = ConfigManager(user_path)
    updated = manager.update(theme="light", recent_tools=["network.ping"])
    assert updated.theme == "light"
    assert ConfigManager(user_path).load() == updated


def test_invalid_json_recovers_to_defaults(tmp_home: Path) -> None:
    user_path = tmp_home / "config.json"
    user_path.write_text("{not json", encoding="utf-8")
    config = ConfigManager(user_path).load()
    assert config == AppConfig()
    assert user_path.exists()
    backups = list(user_path.parent.glob("config.json.broken-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{not json"


def test_empty_config_recovers_to_defaults(tmp_home: Path) -> None:
    user_path = tmp_home / "config.json"
    user_path.write_text("", encoding="utf-8")
    config = ConfigManager(user_path).load()
    assert config == AppConfig()


def test_non_object_config_recovers_to_defaults(tmp_home: Path) -> None:
    user_path = tmp_home / "config.json"
    user_path.write_text("[1, 2, 3]", encoding="utf-8")
    config = ConfigManager(user_path).load()
    assert config == AppConfig()


def test_invalid_values_recover_to_defaults(tmp_home: Path) -> None:
    user_path = tmp_home / "config.json"
    user_path.write_text(
        json.dumps({"theme": "neon", "tasks": {"max_workers": 0}}),
        encoding="utf-8",
    )
    config = ConfigManager(user_path).load()
    assert config.theme == "dark"
    assert config.tasks.max_workers == 8


def test_old_version_config_unknown_fields_are_ignored(tmp_home: Path) -> None:
    user_path = tmp_home / "config.json"
    user_path.write_text(
        json.dumps({"legacy_flag": True, "window": {"legacy_size": 999}}),
        encoding="utf-8",
    )
    config = ConfigManager(user_path).load()
    assert config.window.width == 1280


def test_missing_fields_are_filled_from_defaults(tmp_home: Path) -> None:
    user_path = tmp_home / "config.json"
    user_path.write_text(json.dumps({"tasks": {}}), encoding="utf-8")
    config = ConfigManager(user_path).load()
    assert config.tasks.max_workers == 8
    assert config.theme == "dark"
