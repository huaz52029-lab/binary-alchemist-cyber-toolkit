"""Generic tool page container shared by every future tool."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.exceptions import ExportError
from core.exporters import ExportManager
from core.result import ToolResult
from core.task import Task
from core.task_manager import TaskManager
from core.tool_definition import BaseTool, ToolDefinition
from ui.bridge import LogBridge, TaskBridge
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
        *,
        tool: BaseTool | None = None,
        task_manager: TaskManager | None = None,
        task_bridge: TaskBridge | None = None,
        exporter_manager: ExportManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._definition = definition
        self._tool = tool
        self._task_manager = task_manager
        self._task_bridge = task_bridge
        self._exporter_manager = exporter_manager
        self._current_task_id: str | None = None
        self._last_result: ToolResult | None = None
        self._logger = logging.getLogger("ui.tool")

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
        self._run_button.clicked.connect(self._submit)
        clear_button = QPushButton("清空", self)
        clear_button.setObjectName("flatButton")
        clear_button.clicked.connect(self._clear)
        copy_button = QPushButton("复制", self)
        copy_button.setObjectName("flatButton")
        copy_button.clicked.connect(self._copy_result)
        export_button = QPushButton("导出", self)
        export_button.setObjectName("flatButton")
        export_button.clicked.connect(self._export_result)
        actions = QHBoxLayout()
        actions.addWidget(self._run_button)
        actions.addWidget(clear_button)
        actions.addStretch(1)
        actions.addWidget(copy_button)
        actions.addWidget(export_button)

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

        if task_bridge is not None:
            task_bridge.task_finished.connect(self._on_task_finished)

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

    def export_result(self, path: Path) -> Path | None:
        """Export the last result through the shared ExportManager."""
        if self._last_result is None or self._exporter_manager is None:
            return None
        return self._exporter_manager.export(self._last_result, path)

    def _submit(self) -> None:
        if self._tool is None or self._task_manager is None:
            # Fallback for custom pages that handle run_requested themselves.
            self.run_requested.emit(self.params())
            return
        try:
            self._current_task_id = self._task_manager.submit_tool(self._tool, self.params())
        except Exception:
            self._logger.exception("Failed to submit tool %s", self._definition.id)
            self._result_panel.show_error("任务提交失败，请查看日志。")
            return
        self.set_running(True)

    def _on_task_finished(self, task: Task) -> None:
        if self._current_task_id is None or task.task_id != self._current_task_id:
            return
        self.set_running(False)
        result = task.result
        if result is None:
            message = task.message or "任务未返回结果。"
            self._result_panel.show_error(message)
            self._command_input.set_validation("invalid", message)
            return
        self._last_result = result
        self._result_panel.show_result(result)
        if result.is_ok:
            self._command_input.set_validation("valid", "")
        else:
            self._command_input.set_validation("invalid", result.summary)

    def _copy_result(self) -> None:
        if self._last_result is not None:
            self._result_panel.copy_to_clipboard()

    def _export_result(self) -> None:
        if self._last_result is None or self._exporter_manager is None:
            return
        file_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出结果",
            "ip_info_result",
            "JSON (*.json);;文本 (*.txt);;CSV (*.csv)",
        )
        if not file_path:
            return
        try:
            exported = self.export_result(Path(file_path))
            self._logger.info("结果已导出：%s", exported)
        except ExportError as exc:
            self._result_panel.show_error(exc.user_message)

    def _clear(self) -> None:
        self._command_input.clear()
        self._result_panel.clear()
