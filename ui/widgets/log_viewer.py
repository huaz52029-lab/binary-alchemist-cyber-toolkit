"""Read-only, color-coded log display."""

from __future__ import annotations

import html
from collections.abc import Mapping

from PySide6.QtGui import QAction, QContextMenuEvent
from PySide6.QtWidgets import QPlainTextEdit, QWidget

_DEFAULT_LOG_COLORS = {
    "DEBUG": "#75849a",
    "INFO": "#a9c3cb",
    "WARNING": "#d9a441",
    "ERROR": "#d06a6a",
    "CRITICAL": "#e05252",
}


class LogViewer(QPlainTextEdit):
    """Displays log lines with per-level colors and automatic trimming."""

    def __init__(
        self,
        *,
        max_lines: int = 5000,
        log_colors: Mapping[str, str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("logViewer")
        self.setReadOnly(True)
        self.setMaximumBlockCount(max_lines)
        self._log_colors = dict(log_colors or _DEFAULT_LOG_COLORS)
        self._auto_scroll = True

    def set_log_colors(self, colors: Mapping[str, str]) -> None:
        self._log_colors = dict(colors)

    def set_auto_scroll(self, enabled: bool) -> None:
        self._auto_scroll = enabled

    def auto_scroll(self) -> bool:
        return self._auto_scroll

    def append_log(self, level: str, message: str) -> None:
        """Append one log line, tinted by level and HTML-escaped."""
        color = self._log_colors.get(level.upper(), "#9aa7b5")
        safe_message = html.escape(message)
        self.appendHtml(f'<span style="color:{color};">{safe_message}</span>')
        if self._auto_scroll:
            scrollbar = self.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def clear_logs(self) -> None:
        self.clear()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = self.createStandardContextMenu()
        if menu is None:
            return
        menu.addSeparator()
        copy_action = QAction("复制全部", menu)
        copy_action.triggered.connect(lambda: self.copy())
        clear_action = QAction("清空", menu)
        clear_action.triggered.connect(self.clear_logs)
        auto_scroll_action = QAction("自动滚动", menu)
        auto_scroll_action.setCheckable(True)
        auto_scroll_action.setChecked(self._auto_scroll)
        auto_scroll_action.toggled.connect(self.set_auto_scroll)
        menu.addAction(copy_action)
        menu.addAction(clear_action)
        menu.addAction(auto_scroll_action)
        menu.exec(event.globalPos())
