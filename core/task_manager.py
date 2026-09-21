"""Bounded thread-pool execution for every long-running operation.

The GUI never runs network, filesystem or analysis work directly. It submits a
callable (usually a tool's ``run`` method) and receives progress/status updates
through listeners; cancellation and timeouts are cooperative.

Timeouts are enforced at the ``wait`` boundary: when a wait expires the cancel
event is set and the task is marked ``TIMEOUT``. A tool blocked in non-cooperative
I/O may linger until that call returns, which is why tools must check the
execution context between steps.
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from core.exceptions import TaskCancelledError, ToolInputError
from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext, Task, TaskStatus
from core.task_result import TaskResult
from core.tool_definition import BaseTool, ToolParameters

TaskListener = Callable[[Task], None]
TaskCallable = Callable[[ExecutionContext], ToolResult]

_RESULT_TO_TASK_STATUS = {
    ResultStatus.SUCCESS: TaskStatus.COMPLETED,
    ResultStatus.PARTIAL: TaskStatus.COMPLETED,
    ResultStatus.FAILED: TaskStatus.FAILED,
    ResultStatus.CANCELLED: TaskStatus.CANCELLED,
    ResultStatus.TIMEOUT: TaskStatus.TIMEOUT,
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TaskManager:
    """Submits, supervises and cancels background tasks."""

    def __init__(
        self,
        *,
        max_workers: int = 8,
        default_timeout: float = 30.0,
        logger: logging.Logger | None = None,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be at least 1")
        if default_timeout <= 0:
            raise ValueError("default_timeout must be positive")
        self._max_workers = max_workers
        self._default_timeout = default_timeout
        self._logger = logger or logging.getLogger("core.tasks")
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="toolkit-task",
        )
        self._tasks: dict[str, Task] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._futures: dict[str, Future[None]] = {}
        self._listeners: list[TaskListener] = []
        self._lock = threading.RLock()
        self._closed = False

    @property
    def max_workers(self) -> int:
        return self._max_workers

    @property
    def default_timeout(self) -> float:
        return self._default_timeout

    def submit(
        self,
        tool_id: str,
        params: Mapping[str, Any],
        fn: TaskCallable,
        *,
        timeout: float | None = None,
    ) -> str:
        """Queue a callable and return its task id.

        *timeout* is stored for bookkeeping; it is enforced when a caller waits on
        the task (see :meth:`wait`).
        """
        if not tool_id.strip():
            raise ToolInputError("tool_id must not be empty", user_message="任务工具标识无效。")
        if timeout is not None and timeout <= 0:
            raise ToolInputError("timeout must be positive", user_message="任务超时设置无效。")
        with self._lock:
            if self._closed:
                raise ToolInputError(
                    "task manager is shut down",
                    user_message="任务管理器已关闭，无法提交新任务。",
                )
            task = Task(task_id=uuid.uuid4().hex, tool_id=tool_id, params=dict(params))
            self._tasks[task.task_id] = task
            self._cancel_events[task.task_id] = threading.Event()
            pending_copy = task.model_copy()
        # Notify PENDING before handing the callable to the pool so the
        # lifecycle order PENDING -> RUNNING -> terminal is preserved.
        self._notify(pending_copy)
        future = self._executor.submit(self._run, task.task_id, fn)
        with self._lock:
            self._futures[task.task_id] = future
        return task.task_id

    def submit_tool(
        self,
        tool: BaseTool,
        params: ToolParameters,
        *,
        timeout: float | None = None,
    ) -> str:
        """Queue a registered tool instance."""
        return self.submit(
            tool.id,
            params,
            lambda context: tool.run(params, context),
            timeout=timeout,
        )

    def get(self, task_id: str) -> Task | None:
        """Return a defensive copy of a task, or ``None`` if unknown."""
        return self._copy(task_id)

    def snapshot(self, task_id: str) -> TaskResult | None:
        """Return an immutable view of a task, or ``None`` if unknown."""
        task = self._copy(task_id)
        return TaskResult.from_task(task) if task is not None else None

    def wait(self, task_id: str, timeout: float | None = None) -> TaskResult:
        """Wait for completion and return the final snapshot.

        If the task is still running after *timeout* seconds (default: the manager's
        ``default_timeout``), it is marked ``TIMEOUT`` and cancellation is requested.
        """
        with self._lock:
            future = self._futures.get(task_id)
            if future is None:
                raise ToolInputError(
                    f"unknown task id: {task_id}",
                    user_message="任务不存在或已被清理。",
                )
        effective_timeout = self._default_timeout if timeout is None else timeout
        copy: Task | None = None
        try:
            future.result(effective_timeout)
        except TimeoutError:
            with self._lock:
                task = self._tasks.get(task_id)
                if task is not None and task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                    task.status = TaskStatus.TIMEOUT
                    task.message = "任务执行超时。"
                    task.finished_at = _utcnow()
                    self._cancel_events[task_id].set()
                    copy = task.model_copy()
            self._logger.warning("Task %s timed out", task_id, extra={"task_id": task_id})
            if copy is not None:
                self._notify(copy)
        snapshot = self.snapshot(task_id)
        if snapshot is None:  # pragma: no cover - defensive
            raise ToolInputError("任务不存在或已被清理。", user_message="任务不存在或已被清理。")
        return snapshot

    def cancel(self, task_id: str) -> bool:
        """Request cancellation; returns whether the task was cancellable."""
        with self._lock:
            event = self._cancel_events.get(task_id)
            task = self._tasks.get(task_id)
            if (
                event is None
                or task is None
                or task.status
                in {
                    TaskStatus.COMPLETED,
                    TaskStatus.FAILED,
                    TaskStatus.CANCELLED,
                    TaskStatus.TIMEOUT,
                }
            ):
                return False
            event.set()
            if task.status is TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                task.message = "任务已取消。"
                task.finished_at = _utcnow()
            copy = task.model_copy()
        self._notify(copy)
        return True

    def cancel_all(self) -> int:
        """Cancel every non-terminal task; returns how many were cancelled."""
        with self._lock:
            cancellable = [
                task_id
                for task_id, task in self._tasks.items()
                if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
            ]
        return sum(self.cancel(task_id) for task_id in cancellable)

    def subscribe(self, listener: TaskListener) -> None:
        """Register a status listener; it is called from worker threads."""
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def unsubscribe(self, listener: TaskListener) -> None:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def active_count(self) -> int:
        with self._lock:
            return sum(
                task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
                for task in self._tasks.values()
            )

    def pending_count(self) -> int:
        with self._lock:
            return sum(task.status is TaskStatus.PENDING for task in self._tasks.values())

    def running_count(self) -> int:
        with self._lock:
            return sum(task.status is TaskStatus.RUNNING for task in self._tasks.values())

    def total_count(self) -> int:
        """Return the number of tasks ever submitted to this manager."""
        with self._lock:
            return len(self._tasks)

    def recent_snapshots(self, limit: int = 10) -> list[TaskResult]:
        """Return the most recently created task snapshots, newest first."""
        with self._lock:
            tasks = sorted(
                self._tasks.values(),
                key=lambda task: task.created_at,
                reverse=True,
            )[:limit]
        return [TaskResult.from_task(task) for task in tasks]

    def shutdown(self, *, wait: bool = False, cancel_running: bool = False) -> None:
        """Stop accepting tasks and release the worker threads."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
        if cancel_running:
            self.cancel_all()
        self._executor.shutdown(wait=wait, cancel_futures=not wait)

    def _run(self, task_id: str, fn: TaskCallable) -> None:
        with self._lock:
            task = self._tasks[task_id]
            event = self._cancel_events[task_id]
        if event.is_set():
            self._finish(
                task_id,
                TaskStatus.CANCELLED,
                ToolResult.from_exception(
                    TaskCancelledError(),
                    cancelled=True,
                ),
                "任务已取消。",
            )
            return
        tool_logger = self._logger.getChild("tool")
        context = ExecutionContext(
            task_id=task_id,
            tool_id=task.tool_id,
            logger=tool_logger,
            cancel_event=event,
            on_progress=lambda progress, message: self._update_progress(task_id, progress, message),
        )
        with self._lock:
            task.status = TaskStatus.RUNNING
            task.started_at = _utcnow()
            copy = task.model_copy()
        self._notify(copy)
        try:
            result = fn(context)
            if not isinstance(result, ToolResult):
                raise TypeError(
                    f"task callable returned {type(result).__name__}, expected ToolResult"
                )
            status = _RESULT_TO_TASK_STATUS[result.status]
            self._finish(task_id, status, result, result.summary)
        except TaskCancelledError as exc:
            self._finish(
                task_id,
                TaskStatus.CANCELLED,
                ToolResult.from_exception(exc, cancelled=True),
                exc.user_message,
            )
        except TimeoutError as exc:
            self._finish(
                task_id,
                TaskStatus.TIMEOUT,
                ToolResult.from_exception(exc, timed_out=True),
                "任务执行超时。",
            )
        except Exception as exc:
            self._logger.exception(
                "Task failed",
                extra={"task_id": task_id, "tool_id": task.tool_id},
            )
            self._finish(task_id, TaskStatus.FAILED, ToolResult.from_exception(exc), "")

    def _finish(
        self,
        task_id: str,
        status: TaskStatus,
        result: ToolResult,
        message: str,
    ) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            if task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
                # Already finalized by a timeout/cancel race; keep that outcome.
                return
            task.status = status
            task.result = result
            task.message = message or result.summary
            task.finished_at = _utcnow()
            copy = task.model_copy()
        self._notify(copy)

    def _update_progress(
        self,
        task_id: str,
        progress: float | None,
        message: str | None,
    ) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status is not TaskStatus.RUNNING:
                return
            if progress is not None:
                task.progress = max(0.0, min(100.0, progress))
            if message is not None:
                task.message = message
            copy = task.model_copy()
        self._notify(copy)

    def _copy(self, task_id: str) -> Task | None:
        with self._lock:
            task = self._tasks.get(task_id)
            return task.model_copy() if task is not None else None

    def _notify(self, task: Task) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(task.model_copy())
            except Exception:  # pragma: no cover - listener isolation
                self._logger.exception("Task listener raised an exception")
