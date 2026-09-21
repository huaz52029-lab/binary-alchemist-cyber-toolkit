"""UI integration for the file analysis tool set."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication

from core.app_context import AppContext
from core.result import ResultStatus
from modules import register_builtin_tools
from ui.bridge import TaskBridge
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


def test_file_tools_registered(
    qapp: QApplication,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    ids = {definition.id for definition in app_context.tool_registry.list_tools()}
    assert {
        "file_analysis.file_info",
        "file_analysis.hashes",
        "file_analysis.strings",
        "file_analysis.entropy",
        "file_analysis.hex_viewer",
        "file_analysis.pe_analysis",
        "file_analysis.ioc",
        "file_analysis.analyzer",
        "file_analysis.batch",
    } <= ids


def test_file_info_runs_through_page(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
    tmp_path: Path,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    tool = app_context.tool_registry.get("file_analysis.file_info")
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
    target = tmp_path / "drag.txt"
    target.write_bytes(b"hello")
    try:
        page._fields["file_path"].set_text(str(target))
        page._run_button.click()
        assert _wait_for(lambda: page._last_result is not None, qapp)
        result = page._last_result
        assert result is not None and result.status is ResultStatus.SUCCESS
        assert result.data[0]["name"] == "drag.txt"
    finally:
        bridge.detach()


def test_drop_file_populates_file_field(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
    tmp_path: Path,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    tool = app_context.tool_registry.get("file_analysis.file_info")
    assert tool is not None
    page = ToolPage(tool.definition, theme_manager)
    target = tmp_path / "dropped.bin"
    target.write_bytes(b"x")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(target))])
    event = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    page.dropEvent(event)
    assert Path(page._fields["file_path"].text()) == target
