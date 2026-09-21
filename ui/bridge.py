"""Qt signal bridges between core services and the UI.

TaskManager listeners run on worker threads; these QObjects translate them into
Qt signals that are delivered to GUI-thread slots via queued connections. The UI
never polls the TaskManager.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal

from core.task import Task, TaskStatus
from core.task_manager import TaskManager


class TaskBridge(QObject):
    """Emits task lifecycle events as Qt signals."""

    task_created = Signal(object)
    task_updated = Signal(object)
    task_finished = Signal(object)

    def __init__(self, task_manager: TaskManager, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._task_manager = task_manager
        task_manager.subscribe(self._on_task)

    def _on_task(self, task: Task) -> None:
        if task.status is TaskStatus.PENDING:
            self.task_created.emit(task)
        elif task.status is TaskStatus.RUNNING:
            self.task_updated.emit(task)
        else:
            self.task_finished.emit(task)

    def detach(self) -> None:
        """Unsubscribe from the TaskManager; call before shutdown."""
        self._task_manager.unsubscribe(self._on_task)


class _BridgeHandler(logging.Handler):
    def __init__(self, bridge: LogBridge) -> None:
        super().__init__()
        self._bridge = bridge

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
        except Exception:  # pragma: no cover - formatting must never break logging
            return
        try:
            self._bridge._emit_message(record.levelname, line)
        except RuntimeError:  # bridge widget already destroyed during shutdown
            return


class LogBridge(QObject):
    """Forwards logging records into the UI as ``(level, formatted line)`` signals."""

    message_emitted = Signal(str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.handler: logging.Handler = _BridgeHandler(self)

    def _emit_message(self, level: str, line: str) -> None:
        self.message_emitted.emit(level, line)
