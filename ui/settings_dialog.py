"""Basic settings dialog: theme, log level and startup options."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from core.config_manager import ConfigManager, LoggingSettings, StartupSettings
from ui.theme import DARK, LIGHT, ThemeManager


class SettingsDialog(QDialog):
    """Edits user settings and persists them through the ConfigManager."""

    settings_applied = Signal()

    def __init__(
        self,
        config_manager: ConfigManager,
        theme_manager: ThemeManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("settingsDialog")
        self.setWindowTitle("设置")
        self.setMinimumWidth(420)
        self._config_manager = config_manager
        self._theme_manager = theme_manager
        config = config_manager.load()

        self._theme_combo = QComboBox(self)
        self._theme_combo.addItem("深色", DARK)
        self._theme_combo.addItem("浅色", LIGHT)
        self._theme_combo.setCurrentIndex(max(0, self._theme_combo.findData(theme_manager.theme)))

        self._level_combo = QComboBox(self)
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            self._level_combo.addItem(level, level)
        self._level_combo.setCurrentIndex(max(0, self._level_combo.findData(config.logging.level)))

        self._load_plugins_check = QCheckBox("启动时加载插件", self)
        self._load_plugins_check.setChecked(config.startup.load_plugins)

        form = QFormLayout()
        form.addRow("主题", self._theme_combo)
        form.addRow("日志级别", self._level_combo)
        form.addRow("启动设置", self._load_plugins_check)

        note = QLabel("主题与日志级别立即生效；启动设置将在下次启动时生效。", self)
        note.setObjectName("settingsNote")
        note.setWordWrap(True)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def _apply(self) -> None:
        theme = self._theme_combo.currentData()
        level = self._level_combo.currentText()
        config = self._config_manager.load()
        self._config_manager.update(
            theme=theme,
            logging=LoggingSettings(level=level, console=config.logging.console),
            startup=StartupSettings(load_plugins=self._load_plugins_check.isChecked()),
        )
        self._theme_manager.set_theme(theme)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            self._theme_manager.apply(app)
        self.settings_applied.emit()
        self.accept()
