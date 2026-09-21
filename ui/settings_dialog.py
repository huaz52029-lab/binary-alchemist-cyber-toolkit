"""Settings dialog: theme, log level, task concurrency and data maintenance."""

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
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.config_manager import ConfigManager, LoggingSettings, StartupSettings, TaskSettings
from core.history.maintenance import DatabaseMaintenance
from ui.theme import DARK, LIGHT, ThemeManager


class SettingsDialog(QDialog):
    """Edits user settings and persists them through the ConfigManager."""

    settings_applied = Signal()

    def __init__(
        self,
        config_manager: ConfigManager,
        theme_manager: ThemeManager,
        parent: QWidget | None = None,
        maintenance: DatabaseMaintenance | None = None,
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

        self._workers_spin = QSpinBox(self)
        self._workers_spin.setRange(1, 64)
        self._workers_spin.setValue(config.tasks.max_workers)
        self._workers_spin.setToolTip("全局后台任务并发上限（重启后生效）")

        form = QFormLayout()
        form.addRow("主题", self._theme_combo)
        form.addRow("日志级别", self._level_combo)
        form.addRow("启动设置", self._load_plugins_check)
        form.addRow("最大并发任务", self._workers_spin)

        note = QLabel("主题与日志级别立即生效；启动设置将在下次启动时生效。", self)
        note.setObjectName("settingsNote")
        note.setWordWrap(True)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        about_button = QPushButton("关于", self)
        about_button.clicked.connect(self._show_about)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        if maintenance is not None:
            layout.addWidget(self._build_maintenance_group(maintenance))
        layout.addWidget(note)
        layout.addWidget(buttons)
        layout.addWidget(about_button)

    @staticmethod
    def _show_about() -> None:
        from ui.about_dialog import AboutDialog

        AboutDialog().exec()

    def _build_maintenance_group(self, maintenance: DatabaseMaintenance) -> QWidget:
        group = QWidget(self)
        group.setObjectName("maintenanceGroup")
        self._orphan_label = QLabel("—", group)
        self._broken_label = QLabel("—", group)
        self._size_label = QLabel("—", group)

        def refresh() -> None:
            orphans = maintenance.orphan_artifact_files()
            broken = maintenance.broken_report_refs()
            size = maintenance.calculate_artifact_size()
            self._orphan_label.setText(str(len(orphans)))
            self._broken_label.setText(str(len(broken)))
            self._size_label.setText(self._format_size(size))

        def clean_orphans() -> None:
            count = len(maintenance.orphan_artifact_files())
            if count == 0:
                QMessageBox.information(self, "数据维护", "没有孤立的结果文件。")
                return
            if (
                QMessageBox.question(
                    self,
                    "数据维护",
                    f"将删除 {count} 个孤立结果文件，此操作不可恢复。是否继续？",
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
            removed = maintenance.cleanup_orphan_artifacts()
            QMessageBox.information(self, "数据维护", f"已删除 {removed} 个孤立结果文件。")
            refresh()

        def remove_broken_refs() -> None:
            count = len(maintenance.broken_report_refs())
            if count == 0:
                QMessageBox.information(self, "数据维护", "没有断链的报告引用。")
                return
            if (
                QMessageBox.question(
                    self,
                    "数据维护",
                    f"将从报告中移除 {count} 条断链任务引用。是否继续？",
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
            removed = maintenance.remove_broken_refs()
            QMessageBox.information(self, "数据维护", f"已移除 {removed} 条断链引用。")
            refresh()

        orphan_button = QPushButton("清理孤立结果文件", group)
        orphan_button.clicked.connect(clean_orphans)
        broken_button = QPushButton("移除断链引用", group)
        broken_button.clicked.connect(remove_broken_refs)

        maintenance_form = QFormLayout(group)
        maintenance_form.addRow("孤立结果文件", self._orphan_label)
        maintenance_form.addRow("断链报告引用", self._broken_label)
        maintenance_form.addRow("结果文件占用", self._size_label)
        maintenance_form.addRow(orphan_button, broken_button)
        refresh()
        return group

    @staticmethod
    def _format_size(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                if unit == "B":
                    return f"{int(value)} B"
                return f"{value:.2f} {unit}"
            value /= 1024
        return f"{size} B"

    def _apply(self) -> None:
        theme = self._theme_combo.currentData()
        level = self._level_combo.currentText()
        config = self._config_manager.load()
        self._config_manager.update(
            theme=theme,
            logging=LoggingSettings(level=level, console=config.logging.console),
            startup=StartupSettings(load_plugins=self._load_plugins_check.isChecked()),
            tasks=TaskSettings(
                max_workers=self._workers_spin.value(),
                default_timeout=config.tasks.default_timeout,
            ),
        )
        self._theme_manager.set_theme(theme)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            self._theme_manager.apply(app)
        self.settings_applied.emit()
        self.accept()
