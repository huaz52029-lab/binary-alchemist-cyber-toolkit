"""UI integration for the network tool set."""

from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtWidgets import QApplication, QComboBox, QSpinBox

from core.app_context import AppContext
from core.result import ResultStatus
from modules import register_builtin_tools
from tests.network.test_tcp_scan import FakeScanClient
from ui.bridge import TaskBridge
from ui.navigation import Navigation
from ui.theme import ThemeManager
from ui.tool_page import ToolPage


def _wait_for(predicate: Callable[[], bool], qapp: QApplication, timeout: float = 8.0) -> bool:
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
    tool_id: str,
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


def test_all_network_tools_registered(
    qapp: QApplication,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    registered = {definition.id for definition in app_context.tool_registry.list_tools()}
    assert {
        "network.ip_info",
        "network.ping",
        "network.tcp_connect",
        "network.tcp_scan",
        "network.dns",
        "network.interfaces",
    } <= registered
    navigation = Navigation(app_context.tool_registry)
    assert {"network.ping", "network.dns"} <= set(navigation._tool_buttons)


def test_ping_page_form_and_localhost_run(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    bridge, page = _build_page(app_context, theme_manager, "network.ping")
    try:
        assert set(page._fields) == {"target", "count", "timeout"}
        assert isinstance(page._fields["count"], QSpinBox)
        assert page._fields["count"].value() == 4
        page._fields["target"].set_text("127.0.0.1")
        page._fields["count"].setValue(2)
        page._run_button.click()
        assert _wait_for(lambda: page._last_result is not None, qapp)
        result = page._last_result
        assert result is not None and result.status is ResultStatus.SUCCESS
        assert len(result.data) == 2
        assert page._result_panel._stack.currentWidget() is page._result_panel._table_view
        assert "成功 2/2" in page._result_panel._summary_label.text()
    finally:
        bridge.detach()


def test_dns_page_builds_choice_combo(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    bridge, page = _build_page(app_context, theme_manager, "network.dns")
    try:
        combo = page._fields["record_type"]
        assert isinstance(combo, QComboBox)
        assert [combo.itemText(index) for index in range(combo.count())] == [
            "A",
            "AAAA",
            "CNAME",
            "MX",
            "NS",
            "TXT",
            "PTR",
            "SOA",
        ]
        assert page.params()["record_type"] == "A"
    finally:
        bridge.detach()


def test_interfaces_page_runs(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    bridge, page = _build_page(app_context, theme_manager, "network.interfaces")
    try:
        page._run_button.click()
        assert _wait_for(lambda: page._last_result is not None, qapp)
        assert page._last_result is not None
        assert page._last_result.status is ResultStatus.SUCCESS
        assert page._result_panel._stack.currentWidget() is page._result_panel._table_view
    finally:
        bridge.detach()


def test_scan_page_cancels_running_task(
    qapp: QApplication,
    theme_manager: ThemeManager,
    app_context: AppContext,
) -> None:
    register_builtin_tools(app_context.tool_registry)
    tool = app_context.tool_registry.get("network.tcp_scan")
    assert tool is not None
    tool._client = FakeScanClient(delay=0.02)
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
        page._fields["target"].set_text("127.0.0.1")
        page._fields["ports"].set_text("1-5000")
        page._run_button.click()
        assert not page._cancel_button.isHidden()
        page._cancel_button.click()
        assert _wait_for(lambda: page._run_button.isEnabled(), qapp)
        assert page._result_panel._stack.currentWidget() is page._result_panel._error_view
        assert "取消" in page._result_panel._error_view.text()
    finally:
        bridge.detach()
