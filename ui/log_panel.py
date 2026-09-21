"""Unified log area: level filter, auto-scroll and live bridge wiring."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.bridge import LogBridge
from ui.theme import ThemeManager
from ui.widgets.log_viewer import LogViewer


class LogPanel(QWidget):
    """Live log stream with a level filter and auto-scroll control."""

    def __init__(
        self,
        theme_manager: ThemeManager,
        bridge: LogBridge | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("logPanel")
        self._theme = theme_manager
        self._filter = "ALL"
        self._viewer = LogViewer(log_colors=theme_manager.palette.log_colors)

        filter_label = QLabel("级别", self)
        self._filter_combo = QComboBox(self)
        self._filter_combo.addItem("全部", "ALL")
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            self._filter_combo.addItem(level, level)
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self._auto_scroll_check = QCheckBox("自动滚动", self)
        self._auto_scroll_check.setChecked(True)
        self._auto_scroll_check.toggled.connect(self._viewer.set_auto_scroll)
        clear_button = QPushButton("清空", self)
        clear_button.setObjectName("flatButton")
        clear_button.clicked.connect(self._viewer.clear_logs)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.addWidget(filter_label)
        toolbar.addWidget(self._filter_combo)
        toolbar.addWidget(self._auto_scroll_check)
        toolbar.addStretch(1)
        toolbar.addWidget(clear_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addLayout(toolbar)
        layout.addWidget(self._viewer)

        theme_manager.theme_changed.connect(self._on_theme_changed)
        if bridge is not None:
            bridge.message_emitted.connect(self.append_message)

    def append_message(self, level: str, line: str) -> None:
        """Append a formatted log line if it passes the level filter."""
        if self._filter != "ALL" and level != self._filter:
            return
        self._viewer.append_log(level, line)

    def clear(self) -> None:
        self._viewer.clear_logs()

    def _on_filter_changed(self, index: int) -> None:
        self._filter = self._filter_combo.itemData(index)

    def _on_theme_changed(self, _theme: str) -> None:
        self._viewer.set_log_colors(self._theme.palette.log_colors)
