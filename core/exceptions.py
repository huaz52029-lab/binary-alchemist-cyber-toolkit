"""Unified exception hierarchy with human-readable messages.

Every error that reaches the user is translated into a short, actionable sentence
through :func:`to_user_message`. Raw tracebacks stay in the error log.
"""

from __future__ import annotations

import socket


class ToolkitError(Exception):
    """Base class for all toolkit-specific errors."""

    def __init__(self, message: str, *, user_message: str | None = None) -> None:
        super().__init__(message)
        self._user_message = user_message

    @property
    def user_message(self) -> str:
        """Short, user-facing description of the problem."""
        if self._user_message:
            return self._user_message
        return "操作失败，请查看日志了解详情。"


class ConfigError(ToolkitError):
    """Configuration file is missing, malformed or invalid."""


class ToolInputError(ToolkitError):
    """Tool parameters are missing or invalid."""


class ToolRegistryError(ToolkitError):
    """Tool registration or lookup failed."""


class PluginError(ToolkitError):
    """Plugin discovery, validation or loading failed."""


class ExportError(ToolkitError):
    """Result export failed."""


class TaskError(ToolkitError):
    """Base class for task execution errors."""


class TaskCancelledError(TaskError):
    """The task was cancelled by the user."""

    def __init__(self, message: str = "任务已取消。") -> None:
        super().__init__(message, user_message=message)


class TaskTimeoutError(TaskError):
    """The task exceeded its time budget."""

    def __init__(self, message: str = "任务执行超时。") -> None:
        super().__init__(message, user_message=message)


class NetworkError(ToolkitError):
    """Network connectivity, socket or protocol failure."""


class FileSystemError(ToolkitError):
    """File system access failure."""


class DependencyMissingError(ToolkitError):
    """An optional third-party dependency is not installed."""


_OS_ERROR_MESSAGES = {
    FileNotFoundError: "找不到指定的文件或目录。",
    PermissionError: "没有足够的权限访问该资源。",
    TimeoutError: "操作超时，请稍后重试。",
    ConnectionError: "网络连接失败，请检查目标地址和网络状态。",
}


def to_user_message(exc: BaseException) -> str:
    """Translate an arbitrary exception into a short human-readable message."""
    if isinstance(exc, ToolkitError):
        return exc.user_message
    if isinstance(exc, socket.gaierror):
        return "域名解析失败，请检查目标地址。"
    for error_type, message in _OS_ERROR_MESSAGES.items():
        if isinstance(exc, error_type):
            return message
    if isinstance(exc, OSError):
        return f"系统操作失败：{exc.strerror or '未知原因'}。"
    return "发生未知错误，请查看日志了解详情。"
