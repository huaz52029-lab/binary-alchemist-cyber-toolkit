"""UI integration for the system security tool set."""

from __future__ import annotations

import time
from collections.abc import Callable

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


def test_system_tools_registered(
    qapp: QApplication,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    ids = {definition.id for definition in app_context.tool_registry.list_tools()}
    assert {
        "system.system_info",
        "system.processes",
        "system.process_detail",
        "system.connections",
        "system.services",
        "system.startup",
        "system.users",
        "system.environment",
        "system.resource_monitor",
        "system.analyzer",
    } <= ids


def test_system_info_runs_through_page(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    tool = app_context.tool_registry.get("system.system_info")
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
        page._run_button.click()
        assert _wait_for(lambda: page._last_result is not None, qapp)
        result = page._last_result
        assert result is not None and result.status is ResultStatus.SUCCESS
        sections = {row["section"] for row in result.data}
        assert "操作系统" in sections
    finally:
        bridge.detach()
