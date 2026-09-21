"""Plugin management page: list, details, enable/disable and tool opening."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.plugin_manager import PluginManager


class PluginPage(QWidget):
    """Lists plugin states and wires enable/disable/refresh actions."""

    open_tool_requested = Signal(str)

    def __init__(self, manager: PluginManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._manager = manager
        self.setObjectName("pluginPage")

        title = QLabel("插件", self)
        title.setObjectName("pageTitle")
        note = QLabel(
            "第三方插件与主程序同进程运行，拥有与当前用户相同的 Python 执行能力；"
            "请只安装可信插件。",
            self,
        )
        note.setObjectName("placeholderMessage")
        note.setWordWrap(True)

        self._table = QTableWidget(0, 6, self)
        self._table.setHorizontalHeaderLabels(("名称", "版本", "状态", "工具数", "作者", "权限"))
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.itemSelectionChanged.connect(self._update_details)
        self._table.cellDoubleClicked.connect(self._on_double_click)

        self._details = QLabel("", self)
        self._details.setObjectName("pluginDetails")
        self._details.setWordWrap(True)

        self._enable_button = QPushButton("启用", self)
        self._disable_button = QPushButton("禁用", self)
        self._refresh_button = QPushButton("刷新", self)
        self._open_dir_button = QPushButton("打开插件目录", self)
        for button in (
            self._enable_button,
            self._disable_button,
            self._refresh_button,
            self._open_dir_button,
        ):
            button.setObjectName("flatButton")
        self._enable_button.clicked.connect(self._enable_selected)
        self._disable_button.clicked.connect(self._disable_selected)
        self._refresh_button.clicked.connect(self.refresh)
        self._open_dir_button.clicked.connect(self._open_plugins_dir)

        actions = QHBoxLayout()
        actions.addWidget(self._enable_button)
        actions.addWidget(self._disable_button)
        actions.addWidget(self._refresh_button)
        actions.addWidget(self._open_dir_button)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addLayout(actions)
        layout.addWidget(self._table, 2)
        layout.addWidget(self._details, 1)
        self.refresh()

    def refresh(self) -> None:
        self._manager.refresh()
        states = self._manager.states
        self._table.setRowCount(len(states))
        for row, state in enumerate(states):
            definition = state.definition
            name = definition.name if definition else state.path.name
            values = (
                name,
                definition.version if definition else "-",
                state.status.value,
                str(len(state.tools)),
                definition.author if definition else "-",
                ", ".join(definition.permissions) if definition else "-",
            )
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(value))
        self._update_details()

    def _selected_id(self) -> str | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._manager.states):
            return None
        state = self._manager.states[row]
        return state.definition.id if state.definition else None

    def _update_details(self) -> None:
        plugin_id = self._selected_id()
        state = self._manager.get(plugin_id) if plugin_id else None
        if state is None or state.definition is None:
            self._details.setText("选择一个插件查看详情。")
            return
        definition = state.definition
        lines = [
            f"ID：{definition.id}",
            f"描述：{definition.description or '-'}",
            f"API：{definition.api_version} · 许可：{definition.license or '-'}",
            f"依赖：{', '.join(definition.dependencies) or '无'}",
            f"工具：{', '.join(state.tools) or '无'}",
            f"路径：{state.path}",
        ]
        if state.error:
            lines.append(f"错误：{state.error}")
        self._details.setText("\n".join(lines))

    def _enable_selected(self) -> None:
        plugin_id = self._selected_id()
        if plugin_id and self._manager.enable(plugin_id):
            self.refresh()

    def _disable_selected(self) -> None:
        plugin_id = self._selected_id()
        if plugin_id and self._manager.disable(plugin_id):
            self.refresh()

    def _on_double_click(self, row: int, _column: int) -> None:
        if row < 0 or row >= len(self._manager.states):
            return
        state = self._manager.states[row]
        if state.tools:
            self.open_tool_requested.emit(state.tools[0])

    def _open_plugins_dir(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._manager.plugins_dir)))
