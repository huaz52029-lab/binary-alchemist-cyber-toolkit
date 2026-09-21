"""Task history and report center page integration."""

from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtWidgets import QApplication

from core.app_context import AppContext
from modules import register_builtin_tools
from ui.history_page import TaskHistoryPage
from ui.report_page import ReportPage
from ui.theme import ThemeManager


def _wait_for(predicate: Callable[[], bool], qapp: QApplication, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    qapp.processEvents()
    return predicate()


def test_history_page_lists_and_views(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    task_id = app_context.task_manager.submit_tool(
        app_context.tool_registry.get("network.ip_info"),
        {"input": "192.168.1.1"},
    )
    app_context.task_manager.wait(task_id, timeout=5.0)
    page = TaskHistoryPage(
        app_context.history_manager,
        theme_manager,
        exporter_manager=app_context.exporter_manager,
    )
    assert page._total == 1
    assert page._table.rowCount() == 1
    page._table.setCurrentCell(0, 0)
    page._view_result()
    assert page._result_panel._stack.currentWidget() is page._result_panel._keyvalue_view


def test_report_page_create_and_render(
    qapp: QApplication,
    app_context: AppContext,
) -> None:
    page = ReportPage(app_context.report_manager)
    page._title_edit.setText("冒烟报告")
    page._create()
    assert len(page._reports) == 1
    assert page._current is not None
    assert page._preview.toPlainText().startswith("# 冒烟报告")
