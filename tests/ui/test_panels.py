from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtWidgets import QApplication

from core.finding import Finding, Severity
from core.result import ResultStatus, ToolResult
from core.task import Task, TaskStatus
from ui.log_panel import LogPanel
from ui.result_panel import ResultPanel
from ui.task_panel import TaskPanel
from ui.theme import ThemeManager


def test_log_panel_filtering(theme_manager: ThemeManager) -> None:
    panel = LogPanel(theme_manager)
    panel.append_message("INFO", "info line")
    panel.append_message("WARNING", "warn line")
    panel._filter_combo.setCurrentIndex(panel._filter_combo.findData("INFO"))
    panel.append_message("WARNING", "hidden warn")
    text = panel._viewer.toPlainText()
    assert "info line" in text
    assert "hidden warn" not in text
    panel.clear()
    assert panel._viewer.toPlainText() == ""


def test_result_panel_routing(theme_manager: ThemeManager) -> None:
    panel = ResultPanel(theme_manager)
    table_result = ToolResult.success("rows", data=[{"host": "127.0.0.1", "port": 80}])
    panel.show_result(table_result)
    assert panel._stack.currentWidget() is panel._table_view

    findings = [Finding(title="缺 Header", severity=Severity.MEDIUM, source="web.headers")]
    finding_result = ToolResult(status=ResultStatus.PARTIAL, summary="1 项", findings=findings)
    panel.show_result(finding_result)
    assert panel._stack.currentWidget() is panel._findings_view
    assert panel._findings_view.rowCount() == 1

    failed = ToolResult.failure("连接失败")
    panel.show_result(failed)
    assert panel._stack.currentWidget() is panel._error_view
    assert "连接失败" in panel._error_view.text()

    panel.show_json({"a": {"b": [1, 2]}})
    assert panel._stack.currentWidget() is panel._json_view
    assert panel._json_view.topLevelItemCount() == 1

    panel.clear()
    assert panel._stack.currentWidget() is panel._empty_view


def test_task_panel_rows_and_clear(qapp: QApplication) -> None:
    panel = TaskPanel()
    now = datetime.now(UTC)
    task = Task(
        tool_id="network.ping",
        status=TaskStatus.RUNNING,
        started_at=now,
        progress=30.0,
    )
    panel.set_task(task)
    assert panel.task_count() == 1
    assert panel._table.rowCount() == 1
    task.status = TaskStatus.FAILED
    task.finished_at = now
    panel.set_task(task)
    assert panel._table.rowCount() == 1
    panel.clear()
    assert panel.task_count() == 0
    assert panel._table.rowCount() == 0
