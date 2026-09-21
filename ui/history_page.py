"""Task history page: search, filters, pagination, detail, delete and re-run."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.history.task_history import TaskHistoryManager
from ui.result_panel import ResultPanel
from ui.theme import ThemeManager

PAGE_SIZE = 50


class TaskHistoryPage(QWidget):
    """Persisted task history with unified ResultPanel reuse."""

    re_run_requested = Signal(str, object)

    def __init__(
        self,
        history_manager: TaskHistoryManager,
        theme_manager: ThemeManager,
        exporter_manager: Any = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._history = history_manager
        self._exporter = exporter_manager
        self._page = 0
        self._total = 0
        self._current_rows: list[dict[str, Any]] = []

        title = QLabel("任务历史", self)
        title.setObjectName("pageTitle")
        self._search = QLineEdit(self)
        self._search.setPlaceholderText("搜索 task_id / tool_id / 名称 / 摘要 / 插件")
        self._search.returnPressed.connect(self.refresh)
        self._tool_filter = QComboBox(self)
        self._category_filter = QComboBox(self)
        self._status_filter = QComboBox(self)
        self._time_filter = QComboBox(self)
        self._time_filter.addItems(["全部", "今天", "最近7天", "最近30天"])
        for combo in (self._tool_filter, self._category_filter):
            combo.setEditable(True)
            line_edit = combo.lineEdit()
            if line_edit is not None:
                line_edit.setPlaceholderText("全部")
        self._status_filter.addItems(["全部", "COMPLETED", "FAILED", "CANCELLED", "TIMEOUT"])
        refresh_button = QPushButton("刷新", self)
        refresh_button.setObjectName("flatButton")
        refresh_button.clicked.connect(self.refresh)

        filters = QHBoxLayout()
        filters.addWidget(self._search, 2)
        filters.addWidget(self._tool_filter, 1)
        filters.addWidget(self._category_filter, 1)
        filters.addWidget(self._status_filter, 1)
        filters.addWidget(self._time_filter, 1)
        filters.addWidget(refresh_button)

        self._table = QTableWidget(0, 5, self)
        self._table.setHorizontalHeaderLabels(("时间", "工具", "状态", "耗时", "摘要"))
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.itemSelectionChanged.connect(self._on_select)

        self._detail = QLabel("选择一个任务查看详情。", self)
        self._detail.setObjectName("pluginDetails")
        self._detail.setWordWrap(True)
        self._result_panel = ResultPanel(theme_manager)

        prev_button = QPushButton("上一页", self)
        next_button = QPushButton("下一页", self)
        prev_button.clicked.connect(self._prev_page)
        next_button.clicked.connect(self._next_page)
        self._page_label = QLabel("", self)
        view_button = QPushButton("查看结果", self)
        re_run_button = QPushButton("重新执行", self)
        export_button = QPushButton("导出", self)
        delete_button = QPushButton("删除", self)
        clear_button = QPushButton("清空历史", self)
        for button in (
            prev_button,
            next_button,
            view_button,
            re_run_button,
            export_button,
            delete_button,
            clear_button,
        ):
            button.setObjectName("flatButton")
        view_button.clicked.connect(self._view_result)
        re_run_button.clicked.connect(self._re_run)
        export_button.clicked.connect(self._export)
        delete_button.clicked.connect(self._delete_selected)
        clear_button.clicked.connect(self._clear)

        pager = QHBoxLayout()
        pager.addWidget(prev_button)
        pager.addWidget(next_button)
        pager.addWidget(self._page_label)
        pager.addStretch(1)
        pager.addWidget(view_button)
        pager.addWidget(re_run_button)
        pager.addWidget(export_button)
        pager.addWidget(delete_button)
        pager.addWidget(clear_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addLayout(filters)
        layout.addWidget(self._table, 2)
        layout.addLayout(pager)
        layout.addWidget(self._detail)
        layout.addWidget(self._result_panel, 2)
        self.refresh()

    def refresh(self) -> None:
        filters = {
            "search": self._search.text().strip(),
            "tool_id": self._tool_filter.currentText().strip(),
            "category": self._category_filter.currentText().strip(),
            "status": self._status_filter.currentText()
            if self._status_filter.currentText() != "全部"
            else "",
            "since": self._since_filter(),
            "limit": PAGE_SIZE,
            "offset": self._page * PAGE_SIZE,
        }
        rows, total = self._history.query(**filters)
        self._current_rows = rows
        self._total = total
        self._table.setRowCount(len(rows))
        for row_index, record in enumerate(rows):
            duration = record.get("duration")
            values = (
                record.get("created_at", "")[:19],
                record.get("tool_name") or record.get("tool_id", ""),
                record.get("status", ""),
                f"{duration:.2f}s" if duration is not None else "-",
                (record.get("summary") or "")[:120],
            )
            for column, value in enumerate(values):
                self._table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self._page_label.setText(f"第 {self._page + 1} 页 · 共 {total} 条")
        self._populate_filter_options()
        self._on_select()

    def _populate_filter_options(self) -> None:
        if self._tool_filter.count() <= 1:
            for tool in self._history.distinct_values("tool_id"):
                self._tool_filter.addItem(tool)
        if self._category_filter.count() <= 1:
            for category in self._history.distinct_values("category"):
                self._category_filter.addItem(category)

    def _since_filter(self) -> str | None:
        choice = self._time_filter.currentText()
        if choice == "全部":
            return None
        days = {"今天": 1, "最近7天": 7, "最近30天": 30}[choice]
        since = datetime.now(UTC) - timedelta(days=days)
        return since.isoformat()

    def _selected_task_id(self) -> str | None:
        row = self._table.currentRow()
        if row < 0 or row >= self._table.rowCount():
            return None
        return str(self._current_rows[row]["task_id"])

    def _on_select(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return
        record = self._history.get(task_id)
        if record is None:
            return
        self._detail.setText(
            "\n".join(
                [
                    f"任务：{record['task_id']}",
                    f"工具：{record['tool_name']}（{record['tool_id']}）",
                    f"状态：{record['status']} · 分类：{record.get('category') or '-'}",
                    f"输入摘要：{record.get('input_summary') or '-'}",
                ]
            )
        )

    def _view_result(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return
        result = self._history.load_result(task_id)
        if result is not None:
            self._result_panel.show_result(result)
        else:
            self._result_panel.show_error("没有可查看的结果数据。")

    def _re_run(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return
        record = self._history.get(task_id)
        if not record or not record.get("params_json"):
            QMessageBox.information(self, "重新执行", "该任务的参数未安全持久化，无法重新执行。")
            return
        if (
            QMessageBox.question(
                self,
                "重新执行",
                "是否确认重新执行该任务？",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            params = json.loads(record["params_json"])
        except (TypeError, json.JSONDecodeError):
            params = {}
        self.re_run_requested.emit(record["tool_id"], params)

    def _export(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return
        result = self._history.load_result(task_id)
        if result is None or self._exporter is None:
            return
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "导出结果",
            f"task_{task_id[:8]}",
            "JSON (*.json);;文本 (*.txt);;CSV (*.csv)",
        )
        if path:
            self._exporter.export(result, Path(path))

    def _delete_selected(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return
        if (
            QMessageBox.question(
                self,
                "删除任务",
                f"确认删除任务 {task_id[:8]}？其 Artifact 将同步删除。",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        ok, message = self._history.delete(task_id)
        if not ok:
            QMessageBox.warning(self, "无法删除", message)
        self.refresh()

    def _clear(self) -> None:
        if (
            QMessageBox.question(
                self,
                "清空历史",
                f"确认清空全部任务历史（当前 {self._total} 条）？",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        _count, message = self._history.clear()
        QMessageBox.information(self, "清空历史", message)
        self.refresh()

    def _prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self.refresh()

    def _next_page(self) -> None:
        if (self._page + 1) * PAGE_SIZE < self._total:
            self._page += 1
            self.refresh()
