"""End-to-end UI integration for the IP Information tool."""

from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtWidgets import QApplication

from core.app_context import AppContext
from core.result import ResultStatus
from modules import register_builtin_tools
from ui.bridge import TaskBridge
from ui.main_window import MainWindow
from ui.theme import ThemeManager
from ui.tool_page import ToolPage


def _wait_for(predicate: Callable[[], bool], qapp: QApplication, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    qapp.processEvents()
    return predicate()


def test_tool_page_executes_ip_tool(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    tool = app_context.tool_registry.get("network.ip_info")
    assert tool is not None
    bridge = TaskBridge(app_context.task_manager)
    page = ToolPage(
        tool.definition,
        theme_manager,
        tool=tool,
        task_manager=app_context.task_manager,
        task_bridge=bridge,
        exporter_manager=app_context.exporter_manager,
    )
    try:
        page._fields["input"].set_text("192.168.1.100/24")
        page._run_button.click()
        assert _wait_for(lambda: page._last_result is not None, qapp)
        result = page._last_result
        assert result is not None and result.status is ResultStatus.SUCCESS
        assert page._result_panel._stack.currentWidget() is page._result_panel._keyvalue_view
        text = page._result_panel.current_text()
        assert "地址：192.168.1.100" in text
        assert "192.168.1.0/24" in text
        page._result_panel.copy_to_clipboard()
        assert "192.168.1.100" in QApplication.clipboard().text()
        exported = page.export_result(app_context.paths.data / "ip.json")
        assert exported is not None and exported.exists()
    finally:
        bridge.detach()


def test_invalid_input_shows_error_without_traceback(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    tool = app_context.tool_registry.get("network.ip_info")
    assert tool is not None
    bridge = TaskBridge(app_context.task_manager)
    page = ToolPage(
        tool.definition,
        theme_manager,
        tool=tool,
        task_manager=app_context.task_manager,
        task_bridge=bridge,
    )
    try:
        page._fields["input"].set_text("999.999.999.999")
        page._run_button.click()
        assert _wait_for(lambda: page._last_result is not None, qapp)
        result = page._last_result
        assert result is not None and result.status is ResultStatus.FAILED
        assert page._result_panel._stack.currentWidget() is page._result_panel._error_view
        assert "无法识别" in page._result_panel._error_view.text()
        assert "Traceback" not in page._result_panel._error_view.text()
    finally:
        bridge.detach()


def test_main_window_opens_tool_page_and_runs(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    window = MainWindow(app_context, theme_manager)
    try:
        window.show()
        qapp.processEvents()
        window._open_tool("network.ip_info")
        page = window._stack.currentWidget()
        assert isinstance(page, ToolPage)
        page._fields["input"].set_text("127.0.0.1")
        page._run_button.click()
        assert _wait_for(lambda: page._last_result is not None, qapp)
        assert page._last_result is not None
        assert page._last_result.data[0]["loopback"] is True
    finally:
        window.close()
        qapp.processEvents()
