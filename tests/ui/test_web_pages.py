"""UI integration for the web security tool set."""

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


def _wait_for(predicate: Callable[[], bool], qapp: QApplication, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    qapp.processEvents()
    return predicate()


def test_web_tools_registered(
    qapp: QApplication,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    ids = {definition.id for definition in app_context.tool_registry.list_tools()}
    assert {
        "web.url_parser",
        "web.http_headers",
        "web.cookie_analysis",
        "web.security_headers",
        "web.tls_info",
        "web.http_analysis",
    } <= ids


def test_url_parser_runs_through_page(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    tool = app_context.tool_registry.get("web.url_parser")
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
        page._fields["url"].set_text("https://example.com:8443/path?a=1#top")
        page._run_button.click()
        assert _wait_for(lambda: page._last_result is not None, qapp)
        result = page._last_result
        assert result is not None and result.status is ResultStatus.SUCCESS
        assert result.data[0]["hostname"] == "example.com"
        assert page._result_panel._stack.currentWidget() is page._result_panel._keyvalue_view
    finally:
        bridge.detach()


def test_web_tools_open_in_main_window(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    window = MainWindow(app_context, theme_manager)
    try:
        window.show()
        qapp.processEvents()
        for tool_id in ("web.url_parser", "web.tls_info", "web.http_analysis"):
            window._open_tool(tool_id)
            page = window._stack.currentWidget()
            assert isinstance(page, ToolPage)
            assert page.definition.id == tool_id
    finally:
        window.close()
        qapp.processEvents()
