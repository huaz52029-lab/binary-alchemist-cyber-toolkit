"""Shared workspace page for the two-way encoding tools."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
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
from ui.theme import ThemeManager
from ui.widgets.command_input import CommandInput


class EncodingToolPage(QWidget):
    """One layout for every encoding tool: input, operations, output, copy/swap/clear.

    Encoding tools declare an ``operation`` parameter (choices such as
    ``encode``/``decode`` or ``transform``); the page derives its buttons from it
    and executes through the shared TaskManager.
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
        self._current_operation = "encode"
        self._logger = logging.getLogger("ui.encoding")

        title = QLabel(definition.name, self)
        title.setObjectName("toolTitle")
        meta = QLabel(f"{definition.id} · v{definition.version}", self)
        meta.setObjectName("toolMeta")
        description = QLabel(definition.description or "暂无描述", self)
        description.setObjectName("toolDescription")
        description.setWordWrap(True)

        self._input = CommandInput(label="输入", mode=CommandInput.MODE_MULTI, parent=self)
        output_label = QLabel("输出", self)
        self._output = QPlainTextEdit(self)
        self._output.setObjectName("encodingOutput")
        self._output.setReadOnly(True)
        self._error_label = QLabel("", self)
        self._error_label.setObjectName("resultError")
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)

        operations = self._operation_choices(definition)
        self._operation_buttons: dict[str, QPushButton] = {}
        operation_group = QButtonGroup(self)
        operation_group.setExclusive(True)
        for value, label in operations:
            button = QPushButton(label, self)
            button.setObjectName("primaryButton" if value == operations[0][0] else "flatButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, op=value: self._run(op))
            operation_group.addButton(button)
            self._operation_buttons[value] = button
        self._current_operation = operations[0][0]
        self._operation_buttons[self._current_operation].setChecked(True)

        self._cancel_button = QPushButton("取消", self)
        self._cancel_button.setObjectName("flatButton")
        self._cancel_button.setVisible(False)
        self._cancel_button.clicked.connect(self._cancel)
        swap_button = QPushButton("交换", self)
        swap_button.setObjectName("flatButton")
        swap_button.clicked.connect(self._swap)
        copy_button = QPushButton("复制输出", self)
        copy_button.setObjectName("flatButton")
        copy_button.clicked.connect(self._copy_output)
        clear_button = QPushButton("清空", self)
        clear_button.setObjectName("flatButton")
        clear_button.clicked.connect(self._clear)
        export_button = QPushButton("导出", self)
        export_button.setObjectName("flatButton")
        export_button.clicked.connect(self._export_result)

        operations_row = QHBoxLayout()
        for button in self._operation_buttons.values():
            operations_row.addWidget(button)
        operations_row.addWidget(self._cancel_button)
        operations_row.addStretch(1)
        operations_row.addWidget(swap_button)
        operations_row.addWidget(copy_button)
        operations_row.addWidget(clear_button)
        operations_row.addWidget(export_button)

        self._progress_label = QLabel("", self)
        self._progress_label.setObjectName("toolProgress")
        self._progress_label.setVisible(False)
        self._log_panel = LogPanel(theme_manager, bridge=log_bridge)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(meta)
        layout.addWidget(description)
        layout.addWidget(self._input, 2)
        layout.addLayout(operations_row)
        layout.addWidget(self._progress_label)
        layout.addWidget(output_label)
        layout.addWidget(self._output, 3)
        layout.addWidget(self._error_label)
        layout.addWidget(self._log_panel, 1)

        if task_bridge is not None:
            task_bridge.task_finished.connect(self._on_task_finished)

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    @staticmethod
    def _operation_choices(definition: ToolDefinition) -> list[tuple[str, str]]:
        for parameter in definition.parameters:
            if parameter.name == "operation":
                choices = parameter.choices or ["encode", "decode"]
                labels = parameter.choice_labels or list(choices)
                return [
                    (value, labels[index] if index < len(labels) else value)
                    for index, value in enumerate(choices)
                ]
        return [("encode", "编码"), ("decode", "解码")]

    def _run(self, operation: str) -> None:
        self._current_operation = operation
        if self._tool is None or self._task_manager is None:
            self.run_requested.emit({"input": self._input.text(), "operation": operation})
            return
        try:
            self._current_task_id = self._task_manager.submit_tool(
                self._tool,
                {"input": self._input.text(), "operation": operation},
            )
        except Exception:
            self._logger.exception("Failed to submit encoding tool %s", self._definition.id)
            self._show_error("任务提交失败，请查看日志。")
            return
        self._error_label.setVisible(False)
        self._progress_label.setText("执行中…")
        self._progress_label.setVisible(True)
        self._cancel_button.setVisible(True)

    def _cancel(self) -> None:
        if self._task_manager is not None and self._current_task_id is not None:
            self._task_manager.cancel(self._current_task_id)

    def _on_task_finished(self, task: Task) -> None:
        if self._current_task_id is None or task.task_id != self._current_task_id:
            return
        self._progress_label.setVisible(False)
        self._cancel_button.setVisible(False)
        result = task.result
        if result is None:
            self._show_error(task.message or "任务未返回结果。")
            return
        self._last_result = result
        if result.is_ok and result.data:
            self._output.setPlainText(str(result.data[0].get("output", "")))
        else:
            self._show_error(result.summary)

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.setVisible(True)

    def _swap(self) -> None:
        output = self._output.toPlainText()
        self._output.setPlainText(self._input.text())
        self._input.set_text(output)

    def _copy_output(self) -> None:
        from PySide6.QtWidgets import QApplication

        text = self._output.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _export_result(self) -> None:
        if self._last_result is None or self._exporter_manager is None:
            return
        file_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出结果",
            "result",
            "JSON (*.json);;文本 (*.txt);;CSV (*.csv)",
        )
        if not file_path:
            return
        try:
            self._exporter_manager.export(self._last_result, Path(file_path))
        except ExportError as exc:
            self._show_error(exc.user_message)

    def _clear(self) -> None:
        self._input.clear()
        self._output.clear()
        self._error_label.setVisible(False)
