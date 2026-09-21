from __future__ import annotations

from PySide6.QtWidgets import QApplication

from core.app_context import AppContext
from ui.main_window import MainWindow
from ui.navigation import PAGE_DASHBOARD, PAGE_HISTORY
from ui.theme import LIGHT, ThemeManager


def test_main_window_builds_and_switches_pages(
    app_context: AppContext,
    theme_manager: ThemeManager,
    qapp: QApplication,
) -> None:
    window = MainWindow(app_context, theme_manager)
    try:
        window.show()
        qapp.processEvents()
        assert window._stack.currentWidget() is window._dashboard
        window._navigation._page_buttons[PAGE_HISTORY].click()
        assert window._stack.currentWidget() is window._history_page
        window._navigation._page_buttons[PAGE_DASHBOARD].click()
        assert window._stack.currentWidget() is window._dashboard
    finally:
        window.close()
        qapp.processEvents()


def test_window_geometry_is_persisted_on_close(
    app_context: AppContext,
    theme_manager: ThemeManager,
    qapp: QApplication,
) -> None:
    window = MainWindow(app_context, theme_manager)
    window.show()
    qapp.processEvents()
    window.resize(1111, 777)
    window.close()
    qapp.processEvents()
    config = app_context.config_manager.load()
    assert config.window.width == 1111
    assert config.window.height == 777


def test_theme_switch_updates_application_stylesheet(
    app_context: AppContext,
    theme_manager: ThemeManager,
    qapp: QApplication,
) -> None:
    window = MainWindow(app_context, theme_manager)
    try:
        theme_manager.set_theme(LIGHT)
        qapp.processEvents()
        assert "light theme" in qapp.styleSheet()
    finally:
        window.close()
        qapp.processEvents()


def test_offscreen_saved_position_is_corrected(
    app_context: AppContext,
    theme_manager: ThemeManager,
    qapp: QApplication,
) -> None:
    app_context.config.window.x = 99999
    app_context.config.window.y = 99999
    window = MainWindow(app_context, theme_manager)
    try:
        window.show()
        qapp.processEvents()
        assert window.x() != 99999
        assert any(
            screen.availableGeometry().intersects(window.frameGeometry())
            for screen in QApplication.screens()
        )
    finally:
        window.close()
        qapp.processEvents()
