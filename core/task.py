"""Task state model and the execution context handed to every tool."""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.exceptions import TaskCancelledError
from core.result import LogEntry, ResultStatus, ToolResult


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TaskStatus(StrEnum):
    """Lifecycle states managed by the TaskManager."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class Task(BaseModel):
    """Runtime state of a single background task."""

    model_config = ConfigDict(validate_assignment=True)

    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    tool_id: str = Field(min_length=1)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=_utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    message: str = ""
    params: dict[str, Any] = Field(default_factory=dict)
    result: ToolResult | None = None


ProgressCallback = Callable[[float, str | None], None]


class ExecutionContext:
    """Bridge handed to a tool so it can log, report progress and cancel safely.

    Tools receive one instance per run and must use it for every side channel:
    :meth:`log`, :meth:`set_progress`, :meth:`is_cancelled` and
    :meth:`raise_if_cancelled`. Log records are mirrored both to the global logger
    (with task/tool ids attached) and to the structured result logs.
    """

    __slots__ = (
        "_cancel_event",
        "_logger",
        "_on_progress",
        "log_entries",
        "started_at",
        "task_id",
        "tool_id",
    )

    def __init__(
        self,
        *,
        task_id: str,
        tool_id: str,
        logger: logging.Logger,
        cancel_event: threading.Event,
        on_progress: ProgressCallback | None = None,
        started_at: datetime | None = None,
    ) -> None:
        self.task_id = task_id
        self.tool_id = tool_id
        self.log_entries: list[LogEntry] = []
        self.started_at = started_at or _utcnow()
        self._logger = logger
        self._cancel_event = cancel_event
        self._on_progress = on_progress

    @property
    def is_cancelled(self) -> bool:
        """Whether cancellation was requested for this task."""
        return self._cancel_event.is_set()

    def raise_if_cancelled(self) -> None:
        """Raise :class:`TaskCancelledError` when cancellation was requested."""
        if self.is_cancelled:
            raise TaskCancelledError()

    def log(self, level: int, message: str) -> None:
        """Emit a log record with task/tool context attached."""
        self._logger.log(
            level,
            message,
            extra={"task_id": self.task_id, "tool_id": self.tool_id},
        )
        self.log_entries.append(LogEntry(level=logging.getLevelName(level), message=message))

    def info(self, message: str) -> None:
        self.log(logging.INFO, message)

    def warning(self, message: str) -> None:
        self.log(logging.WARNING, message)

    def error(self, message: str) -> None:
        self.log(logging.ERROR, message)

    def set_progress(self, progress: float, message: str | None = None) -> None:
        """Report progress (0-100) and an optional human-readable message."""
        if self._on_progress is not None:
            self._on_progress(progress, message)

    def make_result(
        self,
        status: ResultStatus,
        summary: str,
        **extra: Any,
    ) -> ToolResult:
        """Build a ToolResult with logs and duration filled in automatically."""
        duration = (datetime.now(UTC) - self.started_at).total_seconds()
        return ToolResult(
            status=status,
            summary=summary,
            logs=list(self.log_entries),
            duration=duration,
            **extra,
        )
