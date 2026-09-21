"""UI integration: encoding pages, dynamic pages and full registry surface."""

from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtWidgets import QApplication

from core.app_context import AppContext
from modules import register_builtin_tools
from ui.bridge import TaskBridge
from ui.encoding_page import EncodingToolPage
from ui.main_window import MainWindow
from ui.navigation import Navigation
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


def test_full_registry_surface(
    qapp: QApplication,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    ids = {definition.id for definition in app_context.tool_registry.list_tools()}
    assert {
        "encoding.base64",
        "encoding.base32",
        "encoding.base58",
        "encoding.hex",
        "encoding.binary",
        "encoding.url",
        "encoding.unicode",
        "encoding.rot13",
        "encoding.rot47",
        "encoding.html_entity",
        "crypto.hash",
        "crypto.md5_reverse",
        "crypto.xor",
        "crypto.jwt",
        "crypto.rsa_helper",
        "ctf.auto_decode",
    } <= ids
    navigation = Navigation(app_context.tool_registry)
    assert {"encoding.base64", "crypto.hash", "ctf.auto_decode"} <= set(navigation._tool_buttons)


def test_base64_page_encode_decode_swap(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    tool = app_context.tool_registry.get("encoding.base64")
    assert tool is not None
    bridge = TaskBridge(app_context.task_manager)
    page = EncodingToolPage(
        tool.definition,
        theme_manager,
        tool=tool,
        task_manager=app_context.task_manager,
        task_bridge=bridge,
        exporter_manager=app_context.exporter_manager,
    )
    try:
        assert list(page._operation_buttons) == ["encode", "decode"]
        page._input.set_text("Hello")
        page._operation_buttons["encode"].click()
        assert _wait_for(lambda: page._output.toPlainText() == "SGVsbG8=", qapp)
        page._input.set_text("SGVsbG8=")
        page._operation_buttons["decode"].click()
        assert _wait_for(lambda: page._output.toPlainText() == "Hello", qapp)
        page._swap()
        assert page._input.text() == "Hello"
    finally:
        bridge.detach()


def test_base64_invalid_decode_shows_error(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    tool = app_context.tool_registry.get("encoding.base64")
    assert tool is not None
    bridge = TaskBridge(app_context.task_manager)
    page = EncodingToolPage(
        tool.definition,
        theme_manager,
        tool=tool,
        task_manager=app_context.task_manager,
        task_bridge=bridge,
    )
    try:
        page._input.set_text("!!!")
        page._operation_buttons["decode"].click()
        assert _wait_for(lambda: page._error_label.isVisibleTo(page), qapp)
        assert "不是有效的Base64" in page._error_label.text()
    finally:
        bridge.detach()


def test_rot13_page_has_transform_button(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    tool = app_context.tool_registry.get("encoding.rot13")
    assert tool is not None
    page = EncodingToolPage(tool.definition, theme_manager)
    assert list(page._operation_buttons) == ["transform"]


def test_main_window_routes_encoding_page(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    window = MainWindow(app_context, theme_manager)
    try:
        window.show()
        qapp.processEvents()
        window._open_tool("encoding.base64")
        assert isinstance(window._stack.currentWidget(), EncodingToolPage)
        window._open_tool("crypto.hash")
        assert isinstance(window._stack.currentWidget(), ToolPage)
    finally:
        window.close()
        qapp.processEvents()


def test_hash_page_mode_visibility(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    tool = app_context.tool_registry.get("crypto.hash")
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
        rows = {parameter.name: row for parameter, row in page._row_meta}
        assert page._form is not None
        assert page._form.isRowVisible(rows["input"])
        assert not page._form.isRowVisible(rows["file_path"])
        page._fields["mode"].setCurrentIndex(page._fields["mode"].findData("file"))
        assert not page._form.isRowVisible(rows["input"])
        assert page._form.isRowVisible(rows["file_path"])
        page._fields["mode"].setCurrentIndex(page._fields["mode"].findData("text"))
        page._fields["input"].set_text("hello")
        page._run_button.click()
        assert _wait_for(lambda: page._last_result is not None, qapp)
        assert page._last_result is not None
        assert page._last_result.data[0]["hash"].startswith("2cf24dba5f")
    finally:
        bridge.detach()
