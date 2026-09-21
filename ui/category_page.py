"""Landing page for a tool category, listing its registered tools."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from core.tool_definition import ToolCategory, ToolDefinition


class CategoryPage(QWidget):
    """Category header plus the tools currently registered under it."""

    tool_selected = Signal(str)

    def __init__(
        self,
        category: ToolCategory,
        tools: Sequence[ToolDefinition],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        title = QLabel(category.display_name, self)
        title.setObjectName("pageTitle")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addWidget(title)
        if not tools:
            empty = QLabel("暂无已注册工具", self)
            empty.setObjectName("emptyState")
            layout.addWidget(empty)
        else:
            for definition in tools:
                button = QPushButton(f"{definition.name} · {definition.id}", self)
                button.setObjectName("categoryToolButton")
                button.clicked.connect(
                    lambda _checked=False, tool_id=definition.id: self.tool_selected.emit(tool_id)
                )
                layout.addWidget(button)
        layout.addStretch(1)
