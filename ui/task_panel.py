"""Task lifecycle table: ID, tool, status, progress, timing and message."""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.task import Task, TaskStatus

_COLUMNS = ("任务 ID", "工具", "状态", "进度", "开始时间", "耗时", "消息")


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    minutes, remainder = divmod(seconds, 60)
    return f"{int(minutes)} 分 {remainder:.0f} 秒"


class TaskPanel(QWidget):
    """Displays task rows and keeps running-task durations fresh."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("taskPanel")
        self._tasks: dict[str, Task] = {}
        self._row_indices: dict[str, int] = {}
        self._table = QTableWidget(0, len(_COLUMNS), self)
        self._table.setObjectName("taskTable")
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setSortingEnabled(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._empty_label = QLabel("暂无任务", self)
        self._empty_label.setObjectName("taskEmpty")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._table)
        self._stack.addWidget(self._empty_label)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self._refresh_running_durations)
        self._refresh_timer.start()

    def set_task(self, task: Task) -> None:
        """Insert or update one task row."""
        self._tasks[task.task_id] = task
        self._upsert_row(task)

    def clear(self) -> None:
        self._tasks.clear()
        self._row_indices.clear()
        self._table.setRowCount(0)
        self._update_empty_state()

    def task_count(self) -> int:
        return len(self._tasks)

    def _upsert_row(self, task: Task) -> None:
        row = self._row_indices.get(task.task_id)
        if row is None or row >= self._table.rowCount():
            self._table.insertRow(0)
            self._row_indices = {task_id: index + 1 for task_id, index in self._row_indices.items()}
            self._row_indices[task.task_id] = 0
            row = 0
        values = self._row_values(task)
        for column, value in enumerate(values):
            self._table.setItem(row, column, QTableWidgetItem(value))
        self._update_empty_state()

    def _row_values(self, task: Task) -> list[str]:
        started = task.started_at
        finished = task.finished_at
        if finished is not None and started is not None:
            duration = (finished - started).total_seconds()
        elif started is not None:
            duration = (datetime.now(UTC) - started).total_seconds()
        else:
            duration = 0.0
        return [
            task.task_id[:8],
            task.tool_id,
            task.status.value,
            f"{task.progress:.0f}%",
            started.astimezone().strftime("%H:%M:%S") if started is not None else "-",
            _format_duration(duration),
            task.message,
        ]

    def _refresh_running_durations(self) -> None:
        for task in self._tasks.values():
            if task.status is TaskStatus.RUNNING:
                self._upsert_row(task)

    def _update_empty_state(self) -> None:
        if self._table.rowCount() == 0:
            self._stack.setCurrentWidget(self._empty_label)
        else:
            self._stack.setCurrentWidget(self._table)
