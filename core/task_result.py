"""Immutable snapshot of a finished task, used for history and export."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from core.result import ToolResult
from core.task import Task, TaskStatus


class TaskResult(BaseModel):
    """A point-in-time, immutable view of a task plus its tool result."""

    model_config = ConfigDict(frozen=True)

    task_id: str
    tool_id: str
    status: TaskStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress: float = 0.0
    message: str = ""
    params: dict[str, Any] = {}
    result: ToolResult | None = None

    @classmethod
    def from_task(cls, task: Task) -> TaskResult:
        """Snapshot the given (possibly still running) task."""
        return cls(
            task_id=task.task_id,
            tool_id=task.tool_id,
            status=task.status,
            created_at=task.created_at,
            started_at=task.started_at,
            finished_at=task.finished_at,
            progress=task.progress,
            message=task.message,
            params=dict(task.params),
            result=task.result,
        )
