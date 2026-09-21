"""Generic metric card used by the dashboard."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class StatusCard(QFrame):
    """A title / value / description card with an optional icon and click signal."""

    clicked = Signal()

    def __init__(
        self,
        *,
        title: str = "",
        value: str = "",
        description: str = "",
        icon: QIcon | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("statusCard")
        self._title_label = QLabel(title, self)
        self._title_label.setObjectName("statusCardTitle")
        self._value_label = QLabel(value, self)
        self._value_label.setObjectName("statusCardValue")
        self._description_label = QLabel(description, self)
        self._description_label.setObjectName("statusCardDescription")
        self._description_label.setWordWrap(True)
        self._icon_label = QLabel(self)
        self._icon_label.setObjectName("statusCardIcon")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._icon_label.setVisible(icon is not None)
        if icon is not None:
            self._icon_label.setPixmap(icon.pixmap(24, 24))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        layout.addWidget(self._title_label)
        layout.addWidget(self._value_label)
        layout.addWidget(self._description_label)
        layout.addWidget(self._icon_label)

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    def set_value(self, value: str | int) -> None:
        self._value_label.setText(str(value))

    def set_description(self, description: str) -> None:
        self._description_label.setText(description)

    def set_icon(self, icon: QIcon | None) -> None:
        self._icon_label.setVisible(icon is not None)
        if icon is not None:
            self._icon_label.setPixmap(icon.pixmap(24, 24))

    def title(self) -> str:
        return self._title_label.text()

    def value(self) -> str:
        return self._value_label.text()

    def description(self) -> str:
        return self._description_label.text()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
