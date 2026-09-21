from __future__ import annotations

from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from core.result import ToolResult
from tests.conftest import DummyTool
from ui.theme import ThemeManager
from ui.tool_page import ToolPage


def test_tool_page_run_signal_and_result(
    qapp: QApplication,
    theme_manager: ThemeManager,
) -> None:
    tool = DummyTool()
    page = ToolPage(tool.definition, theme_manager)
    assert page.definition.id == "system.dummy"
    spy = QSignalSpy(page.run_requested)
    page._fields["input"].set_text("hello")
    page._run_button.click()
    assert spy.count() == 1
    assert spy.at(0)[0] == {"input": "hello"}
    page.show_result(ToolResult.success("ok", data=[{"a": 1}]))
    assert page._result_panel._stack.currentWidget() is page._result_panel._table_view
    page.set_running(True)
    assert not page._run_button.isEnabled()
