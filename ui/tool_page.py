"""Generic tool page container shared by every future tool."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.result import ToolResult
from core.tool_definition import ToolDefinition
from ui.bridge import LogBridge
from ui.log_panel import LogPanel
from ui.result_panel import ResultPanel
from ui.theme import ThemeManager
from ui.widgets.command_input import CommandInput


class ToolPage(QWidget):
    """A tool-agnostic workspace: header, input, actions, result and log areas.

    Future tools (Ping, DNS, Hash, PE analysis, ...) are built on top of this
    container by replacing the default input widget and handling ``run_requested``.
    """

    run_requested = Signal(object)

    def __init__(
        self,
        definition: ToolDefinition,
        theme_manager: ThemeManager,
        log_bridge: LogBridge | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._definition = definition

        title = QLabel(definition.name, self)
        title.setObjectName("toolTitle")
        meta = QLabel(
            f"{definition.id} · v{definition.version}"
            + (f" · {definition.author}" if definition.author else ""),
            self,
        )
        meta.setObjectName("toolMeta")
        description = QLabel(definition.description or "暂无描述", self)
        description.setObjectName("toolDescription")
        description.setWordWrap(True)

        self._command_input = CommandInput(
            label="输入",
            placeholder=f"为 {definition.name} 提供输入参数",
        )
        self._input_host = QVBoxLayout()
        self._input_host.setContentsMargins(0, 0, 0, 0)
        self._input_host.addWidget(self._command_input)

        self._run_button = QPushButton("运行", self)
        self._run_button.setObjectName("primaryButton")
        self._run_button.clicked.connect(lambda: self.run_requested.emit(self.params()))
        clear_button = QPushButton("清空", self)
        clear_button.setObjectName("flatButton")
        clear_button.clicked.connect(self._clear)
        actions = QHBoxLayout()
        actions.addWidget(self._run_button)
        actions.addWidget(clear_button)
        actions.addStretch(1)

        self._result_panel = ResultPanel(theme_manager)
        self._log_panel = LogPanel(theme_manager, bridge=log_bridge)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(meta)
        layout.addWidget(description)
        layout.addLayout(self._input_host)
        layout.addLayout(actions)
        layout.addWidget(self._result_panel, 3)
        layout.addWidget(self._log_panel, 2)

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    def set_input_widget(self, widget: QWidget) -> None:
        """Replace the default single-line input with a tool-specific form."""
        self._command_input.setParent(None)
        self._command_input.deleteLater()
        self._input_host.addWidget(widget)

    def set_running(self, running: bool) -> None:
        self._run_button.setDisabled(running)
        self._run_button.setText("运行中…" if running else "运行")

    def params(self) -> dict[str, Any]:
        return {"input": self._command_input.text()}

    def show_result(self, result: ToolResult) -> None:
        self._result_panel.show_result(result)

    def _clear(self) -> None:
        self._command_input.clear()
        self._result_panel.clear()
