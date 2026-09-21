from __future__ import annotations

from pathlib import Path

from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from core.tool_registry import ToolRegistry
from tests.conftest import DummyTool
from ui.icons import IconProvider
from ui.navigation import PAGE_DASHBOARD, PAGE_HISTORY, Navigation


def test_pages_present_with_empty_registry(qapp: QApplication, tmp_path: Path) -> None:
    navigation = Navigation(ToolRegistry(), icons=IconProvider(tmp_path / "icons"))
    assert navigation.select_page(PAGE_DASHBOARD)
    assert navigation.select_page(PAGE_HISTORY)
    assert not navigation.select_page("nope")


def test_page_changed_signal(qapp: QApplication, tmp_path: Path) -> None:
    navigation = Navigation(ToolRegistry(), icons=IconProvider(tmp_path / "icons"))
    spy = QSignalSpy(navigation.page_changed)
    navigation._page_buttons[PAGE_HISTORY].click()
    assert spy.count() == 1
    assert spy.at(0)[0] == PAGE_HISTORY


def test_registered_tool_is_listed_and_selectable(
    qapp: QApplication,
    tmp_path: Path,
) -> None:
    registry = ToolRegistry()
    registry.register(DummyTool())
    navigation = Navigation(registry, icons=IconProvider(tmp_path / "icons"))
    spy = QSignalSpy(navigation.tool_selected)
    navigation._tool_buttons["system.dummy"].click()
    assert spy.count() == 1
    assert spy.at(0)[0] == "system.dummy"
