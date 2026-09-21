"""Left navigation: fixed pages plus a registry-driven tool tree."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.tool_definition import ToolCategory
from core.tool_registry import ToolRegistry
from ui.icons import IconProvider

PAGE_DASHBOARD = "dashboard"
PAGE_HISTORY = "history"
PAGE_REPORTS = "reports"
PAGE_PLUGINS = "plugins"
PAGE_SETTINGS = "settings"

_CATEGORY_ICONS = {
    ToolCategory.NETWORK: "network",
    ToolCategory.WEB: "web",
    ToolCategory.ENCODING: "encoding",
    ToolCategory.CRYPTO: "crypto",
    ToolCategory.FILE_ANALYSIS: "file",
    ToolCategory.SYSTEM: "system",
    ToolCategory.CTF: "ctf",
}


class Navigation(QWidget):
    """Emits page ids and tool ids; it never executes tools itself."""

    page_changed = Signal(str)
    tool_selected = Signal(str)

    def __init__(
        self,
        registry: ToolRegistry,
        parent: QWidget | None = None,
        *,
        icons: IconProvider | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("navigation")
        self._icons = icons or IconProvider()
        self._page_buttons: dict[str, QPushButton] = {}
        self._tool_buttons: dict[str, QPushButton] = {}
        self._page_group = QButtonGroup(self)
        self._page_group.setExclusive(True)
        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)

        content = QWidget(self)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(2)
        self._add_page(layout, PAGE_DASHBOARD, "工作台", "dashboard")
        self._add_section(layout, "工具")
        registered_tools = registry.list_tools()
        for category in ToolCategory:
            self._add_page(layout, category.value, category.display_name, _CATEGORY_ICONS[category])
            for definition in registry.list_tools(category=category):
                self._add_tool(layout, definition.id, definition.name, definition.icon)
        if not registered_tools:
            empty = QLabel("暂无已注册工具", content)
            empty.setObjectName("navEmpty")
            layout.addWidget(empty)
        self._add_section(layout, "系统")
        self._add_page(layout, PAGE_HISTORY, "任务历史", "history")
        self._add_page(layout, PAGE_REPORTS, "报告中心", "reports")
        self._add_page(layout, PAGE_PLUGINS, "插件", "plugins")
        self._add_page(layout, PAGE_SETTINGS, "设置", "settings")
        layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.setMinimumWidth(220)
        self.setMaximumWidth(320)

    def select_page(self, page_id: str) -> bool:
        """Programmatically select a page without emitting a signal."""
        button = self._page_buttons.get(page_id)
        if button is None:
            return False
        self._clear_tool_checks()
        button.setChecked(True)
        return True

    def _add_section(self, layout: QVBoxLayout, text: str) -> None:
        label = QLabel(text, self)
        label.setObjectName("navSection")
        layout.addWidget(label)

    def _add_page(
        self,
        layout: QVBoxLayout,
        page_id: str,
        label: str,
        icon_name: str,
    ) -> None:
        button = QPushButton(label, self)
        button.setObjectName("navButton")
        button.setCheckable(True)
        button.setIcon(self._icons.icon(icon_name))
        button.clicked.connect(lambda _checked=False, pid=page_id: self._on_page_clicked(pid))
        self._page_group.addButton(button)
        self._page_buttons[page_id] = button
        layout.addWidget(button)

    def _add_tool(
        self,
        layout: QVBoxLayout,
        tool_id: str,
        label: str,
        icon_name: str,
    ) -> None:
        button = QPushButton(label, self)
        button.setObjectName("navToolButton")
        button.setCheckable(True)
        if icon_name:
            button.setIcon(self._icons.icon(icon_name))
        button.clicked.connect(lambda _checked=False, tid=tool_id: self._on_tool_clicked(tid))
        self._tool_group.addButton(button)
        self._tool_buttons[tool_id] = button
        layout.addWidget(button)

    def _on_page_clicked(self, page_id: str) -> None:
        self._clear_tool_checks()
        self.page_changed.emit(page_id)

    def _on_tool_clicked(self, tool_id: str) -> None:
        self._clear_page_checks()
        self.tool_selected.emit(tool_id)

    def _clear_page_checks(self) -> None:
        self._page_group.setExclusive(False)
        for button in self._page_buttons.values():
            button.setChecked(False)
        self._page_group.setExclusive(True)

    def _clear_tool_checks(self) -> None:
        self._tool_group.setExclusive(False)
        for button in self._tool_buttons.values():
            button.setChecked(False)
        self._tool_group.setExclusive(True)
