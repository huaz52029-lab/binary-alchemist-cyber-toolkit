"""Unified logging configuration for the whole application.

Three rotating files are maintained:

* ``logs/app.log`` - every record;
* ``logs/error.log`` - ERROR and CRITICAL only;
* ``logs/security.log`` - security-relevant events from the ``security`` logger.

Business modules simply call ``logging.getLogger(__name__)``; the root logger carries
the configured handlers. Records support ``task_id`` / ``tool_id`` extras which the
formatter renders when present.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final

from core.exceptions import ConfigError

LOG_FORMAT: Final = (
    "%(asctime)s | %(levelname)-8s | %(name)s | task=%(task_id)s | tool=%(tool_id)s | %(message)s"
)
DATE_FORMAT: Final = "%Y-%m-%d %H:%M:%S"
MAX_LOG_BYTES: Final = 5 * 1024 * 1024
BACKUP_COUNT: Final = 5

_LEVELS: Final = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _coerce_level(level: str) -> int:
    try:
        return _LEVELS[level.upper()]
    except KeyError as exc:
        raise ConfigError(
            f"invalid log level: {level}",
            user_message="日志级别配置无效，已使用默认值 INFO。",
        ) from exc


class _ContextFilter(logging.Filter):
    """Fill task/tool placeholders with '-' when a record carries no context."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.task_id = getattr(record, "task_id", "-")
        record.tool_id = getattr(record, "tool_id", "-")
        return True


class LoggerManager:
    """Configures and owns the application logging handlers."""

    def __init__(
        self,
        logs_dir: Path,
        *,
        level: str = "INFO",
        console: bool = True,
    ) -> None:
        self._logs_dir = Path(logs_dir)
        self._level = _coerce_level(level)
        self._console_enabled = console
        self._configured = False
        self._handlers: list[logging.Handler] = []
        self._console_handler: logging.Handler | None = None
        self._context_filter = _ContextFilter()
        self._formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    @property
    def logs_dir(self) -> Path:
        return self._logs_dir

    @property
    def security_logger(self) -> logging.Logger:
        """Logger reserved for security-relevant events."""
        return logging.getLogger("security")

    def get_logger(self, name: str) -> logging.Logger:
        """Return a logger for a component; handlers live on the root logger."""
        return logging.getLogger(name)

    def setup(self) -> None:
        """Configure handlers once; repeated calls are no-ops."""
        if self._configured:
            return
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        for handler in self._build_handlers():
            root.addHandler(handler)
            self._handlers.append(handler)
        security = self.security_logger
        security.propagate = False
        security.setLevel(self._level)
        security_handler = self._file_handler("security.log")
        security.addHandler(security_handler)
        self._handlers.append(security_handler)
        self._configured = True

    def attach_sink(self, handler: logging.Handler) -> None:
        """Attach an extra sink (e.g. a Qt signal handler for the log panel)."""
        handler.setFormatter(self._formatter)
        handler.addFilter(self._context_filter)
        logging.getLogger().addHandler(handler)
        self._handlers.append(handler)

    def set_level(self, level: str) -> None:
        """Change the effective log level at runtime."""
        self._level = _coerce_level(level)
        if self._console_handler is not None:
            self._console_handler.setLevel(self._level)
        self.security_logger.setLevel(self._level)

    def shutdown(self) -> None:
        """Detach and close the handlers owned by this manager."""
        root = logging.getLogger()
        for handler in self._handlers:
            root.removeHandler(handler)
            self.security_logger.removeHandler(handler)
            handler.close()
        self._handlers.clear()
        self._configured = False

    def _build_handlers(self) -> list[logging.Handler]:
        handlers: list[logging.Handler] = []
        if self._console_enabled:
            console = logging.StreamHandler()
            console.setLevel(self._level)
            self._console_handler = console
            handlers.append(console)
        app_file = self._file_handler("app.log", level=logging.DEBUG)
        error_file = self._file_handler("error.log", level=logging.ERROR)
        handlers.extend((app_file, error_file))
        return handlers

    def _file_handler(self, filename: str, *, level: int = logging.DEBUG) -> RotatingFileHandler:
        handler = RotatingFileHandler(
            self._logs_dir / filename,
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setLevel(level)
        handler.setFormatter(self._formatter)
        handler.addFilter(self._context_filter)
        return handler
