from __future__ import annotations

from pathlib import Path

import pytest

from core.exceptions import ConfigError
from core.logger import LoggerManager


def _setup(tmp_path: Path) -> LoggerManager:
    manager = LoggerManager(tmp_path / "logs", console=False)
    manager.setup()
    return manager


def test_app_and_error_logs_are_split(tmp_path: Path) -> None:
    manager = _setup(tmp_path)
    logger = manager.get_logger("tests.sample")
    try:
        logger.info("info message")
        logger.error("error message")
    finally:
        manager.shutdown()
    app_log = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    error_log = (tmp_path / "logs" / "error.log").read_text(encoding="utf-8")
    assert "info message" in app_log
    assert "error message" in app_log
    assert "error message" in error_log
    assert "info message" not in error_log


def test_records_carry_task_and_tool_ids(tmp_path: Path) -> None:
    manager = _setup(tmp_path)
    logger = manager.get_logger("tests.sample")
    try:
        logger.info(
            "contextual message",
            extra={"task_id": "t-1", "tool_id": "network.ping"},
        )
    finally:
        manager.shutdown()
    app_log = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    assert "task=t-1" in app_log
    assert "tool=network.ping" in app_log


def test_security_logger_is_isolated(tmp_path: Path) -> None:
    manager = _setup(tmp_path)
    try:
        manager.security_logger.warning("security event")
    finally:
        manager.shutdown()
    security_log = (tmp_path / "logs" / "security.log").read_text(encoding="utf-8")
    app_log = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    assert "security event" in security_log
    assert "security event" not in app_log


def test_invalid_level_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        LoggerManager(tmp_path / "logs", level="LOUD")
