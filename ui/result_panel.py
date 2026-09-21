"""Unified result area with stacked text / JSON / table / findings / error views."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QApplication,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.finding import Finding
from core.result import ResultStatus, ToolResult
from ui.theme import ThemeManager
from ui.widgets.result_table import ResultTable


class ResultPanel(QWidget):
    """Renders a ToolResult through the most appropriate view."""

    _FINDING_COLUMNS = ("等级", "类型", "标题", "描述", "证据", "建议", "来源")

    def __init__(self, theme_manager: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("resultPanel")
        self._theme = theme_manager
        self._last_findings: list[Finding] = []

        self._summary_label = QLabel("", self)
        self._summary_label.setObjectName("resultSummary")
        self._summary_label.setWordWrap(True)
        self._summary_label.setVisible(False)

        self._stack = QStackedWidget(self)
        self._empty_view = QLabel("暂无结果", self)
        self._empty_view.setObjectName("resultEmpty")
        self._empty_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_view = QPlainTextEdit(self)
        self._text_view.setObjectName("resultText")
        self._text_view.setReadOnly(True)
        self._json_view = QTreeWidget(self)
        self._json_view.setObjectName("resultJson")
        self._json_view.setHeaderLabels(("字段", "值"))
        self._json_view.setAlternatingRowColors(True)
        self._table_view = ResultTable(self)
        self._findings_view = QTableWidget(0, len(self._FINDING_COLUMNS), self)
        self._findings_view.setObjectName("resultFindings")
        self._findings_view.setHorizontalHeaderLabels(self._FINDING_COLUMNS)
        self._findings_view.setAlternatingRowColors(True)
        self._findings_view.setSortingEnabled(True)
        self._findings_view.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._findings_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._keyvalue_view = QTableWidget(0, 3, self)
        self._keyvalue_view.setObjectName("resultKeyValues")
        self._keyvalue_view.setHorizontalHeaderLabels(("分组", "字段", "值"))
        self._keyvalue_view.setAlternatingRowColors(True)
        self._keyvalue_view.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._keyvalue_view.verticalHeader().setVisible(False)
        self._keyvalue_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._keyvalue_view.horizontalHeader().setStretchLastSection(True)
        self._keyvalue_rows: list[tuple[str, str, str]] = []
        self._keyvalue_title = ""
        self._last_json_payload: Any = None
        self._error_view = QLabel("", self)
        self._error_view.setObjectName("resultError")
        self._error_view.setWordWrap(True)
        for view in (
            self._empty_view,
            self._text_view,
            self._json_view,
            self._table_view,
            self._findings_view,
            self._keyvalue_view,
            self._error_view,
        ):
            self._stack.addWidget(view)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._summary_label)
        layout.addWidget(self._stack)

        theme_manager.theme_changed.connect(self._on_theme_changed)

    def clear(self) -> None:
        self.show_empty()

    def show_empty(self) -> None:
        self._summary_label.setVisible(False)
        self._stack.setCurrentWidget(self._empty_view)

    def show_text(self, text: str) -> None:
        self._text_view.setPlainText(text)
        self._stack.setCurrentWidget(self._text_view)

    def show_json(self, payload: dict[str, Any] | list[Any] | str) -> None:
        if isinstance(payload, str):
            raw = payload
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                self.show_text(raw)
                return
        self._last_json_payload = payload
        self._json_view.clear()
        if isinstance(payload, dict):
            for key, value in payload.items():
                item = QTreeWidgetItem([str(key), ""])
                self._populate_json_item(item, value)
                self._json_view.addTopLevelItem(item)
        else:
            root = QTreeWidgetItem(["root", ""])
            self._populate_json_item(root, payload)
            self._json_view.addTopLevelItem(root)
        self._stack.setCurrentWidget(self._json_view)

    def show_table(self, columns: list[str], rows: list[list[Any]]) -> None:
        self._table_view.set_columns(columns)
        self._table_view.set_rows(rows)
        self._stack.setCurrentWidget(self._table_view)

    def show_findings(self, findings: list[Finding]) -> None:
        self._last_findings = findings
        self._findings_view.setRowCount(len(findings))
        for row, finding in enumerate(findings):
            values = (
                finding.severity.value,
                finding.kind.value,
                finding.title,
                finding.description,
                finding.evidence,
                finding.recommendation or "",
                finding.source,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setForeground(
                        QBrush(QColor(self._theme.severity_color(finding.severity.value)))
                    )
                self._findings_view.setItem(row, column, item)
        self._stack.setCurrentWidget(self._findings_view)

    def show_key_values(self, spec: Mapping[str, Any], data: Mapping[str, Any]) -> None:
        """Render a single structured record as grouped 字段/值 rows.

        ``spec`` comes from ``ToolResult.metadata["display"]``; items with a
        missing or ``None`` field value are skipped (e.g. IPv6 broadcast).
        """
        rows: list[tuple[str, str, str]] = []
        title = str(spec.get("title", "结果"))
        for section in spec.get("sections") or []:
            section_title = str(section.get("title", ""))
            for item in section.get("items") or []:
                field = item.get("field")
                if not field or field not in data:
                    continue
                value = data.get(field)
                if value is None:
                    continue
                label = str(item.get("label", field))
                value_map = item.get("map")
                if isinstance(value, bool):
                    display = "是" if value else "否"
                elif isinstance(value_map, dict):
                    display = value_map.get(str(value), str(value))
                else:
                    display = str(value)
                rows.append((section_title, label, display))
        self._keyvalue_rows = rows
        self._keyvalue_title = title
        table = self._keyvalue_view
        table.setRowCount(len(rows))
        for row, (section, label, value) in enumerate(rows):
            table.setItem(row, 0, QTableWidgetItem(section))
            table.setItem(row, 1, QTableWidgetItem(label))
            table.setItem(row, 2, QTableWidgetItem(value))
        self._stack.setCurrentWidget(self._keyvalue_view)

    def show_error(self, message: str) -> None:
        self._error_view.setText(message)
        self._stack.setCurrentWidget(self._error_view)

    def show_result(self, result: ToolResult) -> None:
        """Route a unified ToolResult to the most informative view."""
        self._summary_label.setText(result.summary or f"状态：{result.status.value}")
        self._summary_label.setVisible(True)
        if result.status is ResultStatus.FAILED or result.status in (
            ResultStatus.CANCELLED,
            ResultStatus.TIMEOUT,
        ):
            self.show_error(result.summary or "任务未成功完成。")
        elif result.data:
            display_spec = result.metadata.get("display")
            if (
                len(result.data) == 1
                and isinstance(display_spec, dict)
                and display_spec.get("sections")
            ):
                self.show_key_values(display_spec, result.data[0])
                return
            columns: list[str] = []
            for row in result.data:
                for key in row:
                    if key not in columns:
                        columns.append(key)
            rows = [[row.get(column) for column in columns] for row in result.data]
            self.show_table(columns, rows)
        elif result.findings:
            self.show_findings(result.findings)
        else:
            self.show_json(result.model_dump(mode="json"))

    def current_text(self) -> str:
        """Plain-text rendering of the active view, used by the copy action."""
        current = self._stack.currentWidget()
        if current is self._keyvalue_view:
            lines = [f"# {self._keyvalue_title}"]
            last_section: str | None = None
            for section, label, value in self._keyvalue_rows:
                if section != last_section:
                    lines.append(f"## {section}")
                    last_section = section
                lines.append(f"{label}：{value}")
            return "\n".join(lines)
        if current is self._text_view:
            return self._text_view.toPlainText()
        if current is self._table_view:
            return self._table_view.to_text()
        if current is self._findings_view:
            return "\n".join(
                f"[{finding.severity.value}|{finding.kind.value}] {finding.title}: "
                f"{finding.description}"
                for finding in self._last_findings
            )
        if current is self._json_view:
            return json.dumps(self._last_json_payload, ensure_ascii=False, indent=2)
        if current is self._error_view:
            return self._error_view.text()
        return ""

    def copy_to_clipboard(self) -> None:
        """Copy the current view as plain text."""
        text = self.current_text()
        if text:
            QApplication.clipboard().setText(text)

    def _populate_json_item(self, parent: QTreeWidgetItem, value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                item = QTreeWidgetItem([str(key), ""])
                self._populate_json_item(item, child)
                parent.addChild(item)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                item = QTreeWidgetItem([f"[{index}]", ""])
                self._populate_json_item(item, child)
                parent.addChild(item)
        else:
            parent.setText(1, "" if value is None else str(value))

    def _on_theme_changed(self, _theme: str) -> None:
        if self._last_findings:
            self.show_findings(self._last_findings)
