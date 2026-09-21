"""UI integration for the MD5 reverse analyzer."""

from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtWidgets import QApplication

from core.app_context import AppContext
from core.result import ResultStatus
from infrastructure.crypto import md5_hexdigest
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


def _build_page(
    app_context: AppContext,
    theme_manager: ThemeManager,
    tool_id: str = "crypto.md5_reverse",
) -> tuple[TaskBridge, ToolPage]:
    register_builtin_tools(app_context.tool_registry)
    tool = app_context.tool_registry.get(tool_id)
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
    return bridge, page


def test_dynamic_field_visibility(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    bridge, page = _build_page(app_context, theme_manager)
    try:
        assert set(page._fields) == {
            "mode",
            "target",
            "candidate",
            "dictionary_path",
            "charset",
            "min_length",
            "max_length",
        }
        rows = {parameter.name: row for parameter, row in page._row_meta}
        assert page._form is not None
        assert page._form.isRowVisible(rows["candidate"])
        assert not page._form.isRowVisible(rows["dictionary_path"])
        assert not page._form.isRowVisible(rows["charset"])
        page._fields["mode"].setCurrentIndex(page._fields["mode"].findData("dictionary"))
        assert not page._form.isRowVisible(rows["candidate"])
        assert page._form.isRowVisible(rows["dictionary_path"])
        page._fields["mode"].setCurrentIndex(page._fields["mode"].findData("bruteforce"))
        assert page._form.isRowVisible(rows["charset"])
        assert page._form.isRowVisible(rows["min_length"])
        assert not page._form.isRowVisible(rows["dictionary_path"])
    finally:
        bridge.detach()


def test_verify_run_via_page(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    bridge, page = _build_page(app_context, theme_manager)
    try:
        page._fields["target"].set_text(md5_hexdigest("hello"))
        page._fields["candidate"].set_text("hello")
        page._run_button.click()
        assert _wait_for(lambda: page._last_result is not None, qapp)
        result = page._last_result
        assert result is not None and result.status is ResultStatus.SUCCESS
        assert "匹配 1/1" in page._result_panel._summary_label.text()
        assert page._result_panel._stack.currentWidget() is page._result_panel._table_view
        assert "是" in page._result_panel.current_text()
    finally:
        bridge.detach()


def test_bruteforce_cancel_via_page(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    bridge, page = _build_page(app_context, theme_manager)
    try:
        page._fields["mode"].setCurrentIndex(page._fields["mode"].findData("bruteforce"))
        page._fields["target"].set_text(md5_hexdigest("hello"))
        page._run_button.click()
        assert not page._cancel_button.isHidden()
        page._cancel_button.click()
        assert _wait_for(lambda: page._run_button.isEnabled(), qapp)
        assert page._result_panel._stack.currentWidget() is page._result_panel._error_view
        assert "取消" in page._result_panel._error_view.text()
    finally:
        bridge.detach()


def test_ctf_entry_opens_same_tool(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    window = MainWindow(app_context, theme_manager)
    try:
        window.show()
        qapp.processEvents()
        window._open_tool("ctf.md5_reverse")
        page = window._stack.currentWidget()
        assert isinstance(page, ToolPage)
        assert page.definition.id == "ctf.md5_reverse"
    finally:
        window.close()
        qapp.processEvents()
