"""Simple page used for features that arrive in later phases."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderPage(QWidget):
    """Title plus an informative message for a not-yet-built feature."""

    def __init__(self, title: str, message: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        title_label = QLabel(title, self)
        title_label.setObjectName("pageTitle")
        message_label = QLabel(message, self)
        message_label.setObjectName("placeholderMessage")
        message_label.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(title_label)
        layout.addWidget(message_label)
        layout.addStretch(1)
