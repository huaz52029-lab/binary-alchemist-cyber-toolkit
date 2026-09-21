from __future__ import annotations

from core.exceptions import (
    ConfigError,
    TaskCancelledError,
    to_user_message,
)


def test_default_user_message() -> None:
    assert ConfigError("raw").user_message == "操作失败，请查看日志了解详情。"


def test_custom_user_message_wins() -> None:
    assert ConfigError("raw", user_message="配置损坏").user_message == "配置损坏"


def test_known_os_errors_are_translated() -> None:
    assert "找不到指定" in to_user_message(FileNotFoundError("x"))
    assert "没有足够" in to_user_message(PermissionError("x"))
    assert "超时" in to_user_message(TimeoutError("x"))


def test_unknown_error_falls_back() -> None:
    assert "未知错误" in to_user_message(RuntimeError("boom"))


def test_cancelled_error_message() -> None:
    assert TaskCancelledError().user_message == "任务已取消。"
