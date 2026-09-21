from __future__ import annotations

from PySide6.QtWidgets import QApplication

from core.app_context import AppContext
from ui.settings_dialog import SettingsDialog
from ui.theme import LIGHT, ThemeManager


def test_apply_persists_settings(
    app_context: AppContext,
    theme_manager: ThemeManager,
    qapp: QApplication,
) -> None:
    dialog = SettingsDialog(app_context.config_manager, theme_manager)
    dialog._theme_combo.setCurrentIndex(dialog._theme_combo.findData(LIGHT))
    dialog._level_combo.setCurrentIndex(dialog._level_combo.findData("DEBUG"))
    dialog._load_plugins_check.setChecked(True)
    dialog._apply()
    config = app_context.config_manager.load()
    assert config.theme == LIGHT
    assert config.logging.level == "DEBUG"
    assert config.startup.load_plugins is True
    assert theme_manager.theme == LIGHT
    assert "light theme" in qapp.styleSheet()
