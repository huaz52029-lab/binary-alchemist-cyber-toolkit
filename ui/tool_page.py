"""Generic tool page container shared by every tool."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPoint, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.exceptions import ExportError
from core.exporters import ExportManager
from core.result import ToolResult
from core.task import Task
from core.task_manager import TaskManager
from core.tool_definition import BaseTool, ToolDefinition, ToolParameterKind
from ui.bridge import LogBridge, TaskBridge
from ui.log_panel import LogPanel
from ui.result_panel import ResultPanel
from ui.theme import ThemeManager
from ui.widgets.command_input import CommandInput


class _FileInput(QWidget):
    """Text input with a native file picker, used for FILE parameters."""

    text_changed = Signal(str)

    def __init__(self, *, placeholder: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._edit = CommandInput(label="", placeholder=placeholder, parent=self)
        browse = QPushButton("选择…", self)
        browse.setObjectName("flatButton")
        browse.clicked.connect(self._browse)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._edit, 1)
        layout.addWidget(browse)
        self._edit.text_changed.connect(self.text_changed)

    def text(self) -> str:
        return self._edit.text()

    def set_text(self, value: str) -> None:
        self._edit.set_text(value)

    def clear(self) -> None:
        self._edit.clear()

    def _browse(self) -> None:
        file_path, _selected_filter = QFileDialog.getOpenFileName(self, "选择文件")
        if file_path:
            self._edit.set_text(file_path)


class ToolPage(QWidget):
    """A tool-agnostic workspace: header, parameter form, actions and results.

    The parameter form is generated from the tool's declarative
    ``ToolDefinition.parameters``; tools never build Qt widgets themselves.
    Execution, cancellation, progress and export all flow through the shared
    TaskManager / TaskBridge / ExportManager services.
    """

    run_requested = Signal(object)
    send_to_requested = Signal(str, str)

    SEND_TO_TARGETS = (
        ("ctf.auto_decode", "Auto Decode"),
        ("ctf.regex", "Regex"),
        ("ctf.text_analysis", "Text Analysis"),
        ("ctf.data_transform", "数据转换"),
        ("crypto.xor", "XOR"),
        ("crypto.hash", "Hash"),
        ("encoding.base64", "Base64"),
        ("encoding.hex", "Hex"),
    )

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
        self._fields: dict[str, QWidget] = {}
        self._form: QFormLayout | None = None
        self._row_meta: list[tuple[Any, int]] = []
        self._logger = logging.getLogger("ui.tool")
        self.setAcceptDrops(True)

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

        self._input_host = QVBoxLayout()
        self._input_host.setContentsMargins(0, 0, 0, 0)
        if definition.parameters:
            form_container = QWidget(self)
            form = QFormLayout(form_container)
            form.setContentsMargins(0, 0, 0, 0)
            form.setSpacing(6)
            self._form = form
            for parameter in definition.parameters:
                field = self._make_field(parameter)
                self._fields[parameter.name] = field
                form.addRow(parameter.label, field)
                self._row_meta.append((parameter, form.rowCount() - 1))
                self._connect_field_changes(field)
            self._update_visibility()
            self._input_host.addWidget(form_container)

        self._run_button = QPushButton("运行", self)
        self._run_button.setObjectName("primaryButton")
        self._run_button.clicked.connect(self._submit)
        self._cancel_button = QPushButton("取消", self)
        self._cancel_button.setObjectName("flatButton")
        self._cancel_button.setVisible(False)
        self._cancel_button.clicked.connect(self._cancel)
        clear_button = QPushButton("清空", self)
        clear_button.setObjectName("flatButton")
        clear_button.clicked.connect(self._clear)
        copy_button = QPushButton("复制", self)
        copy_button.setObjectName("flatButton")
        copy_button.clicked.connect(self._copy_result)
        export_button = QPushButton("导出", self)
        export_button.setObjectName("flatButton")
        export_button.clicked.connect(self._export_result)
        send_to_button = QPushButton("发送到", self)
        send_to_button.setObjectName("flatButton")
        send_to_button.clicked.connect(self._show_send_to_menu)
        self._send_to_button = send_to_button
        actions = QHBoxLayout()
        actions.addWidget(self._run_button)
        actions.addWidget(self._cancel_button)
        actions.addWidget(clear_button)
        actions.addStretch(1)
        actions.addWidget(copy_button)
        actions.addWidget(export_button)
        actions.addWidget(send_to_button)

        self._progress_label = QLabel("", self)
        self._progress_label.setObjectName("toolProgress")
        self._progress_label.setVisible(False)

        self._result_panel = ResultPanel(theme_manager)
        self._detail_view = QPlainTextEdit(self)
        self._detail_view.setObjectName("detailViewer")
        self._detail_view.setReadOnly(True)
        self._detail_view.setMaximumHeight(120)
        self._detail_view.setVisible(False)
        self._log_panel = LogPanel(theme_manager, bridge=log_bridge)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(meta)
        layout.addWidget(description)
        layout.addLayout(self._input_host)
        layout.addLayout(actions)
        layout.addWidget(self._progress_label)
        layout.addWidget(self._result_panel, 3)
        layout.addWidget(self._detail_view)
        layout.addWidget(self._log_panel, 2)

        self._result_panel.row_activated.connect(self._show_row_detail)
        if task_bridge is not None:
            task_bridge.task_finished.connect(self._on_task_finished)
            task_bridge.task_updated.connect(self._on_task_updated)

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    def set_input_widget(self, widget: QWidget) -> None:
        """Replace the generated form with a fully custom input widget."""
        for field in self._fields.values():
            field.setParent(None)
            field.deleteLater()
        self._fields.clear()
        self._input_host.addWidget(widget)

    def set_running(self, running: bool) -> None:
        self._run_button.setDisabled(running)
        self._run_button.setText("运行中…" if running else "运行")
        self._cancel_button.setVisible(running)
        if not running:
            self._progress_label.setVisible(False)

    def params(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for name, widget in self._fields.items():
            if isinstance(widget, CommandInput):
                values[name] = widget.text()
            elif isinstance(widget, QSpinBox):
                values[name] = widget.value()
            elif isinstance(widget, QComboBox):
                values[name] = widget.currentData()
            elif isinstance(widget, _FileInput):
                values[name] = widget.text()
        return values

    def show_result(self, result: ToolResult) -> None:
        self._result_panel.show_result(result)

    def export_result(self, path: Path) -> Path | None:
        """Export the last result through the shared ExportManager."""
        if self._last_result is None or self._exporter_manager is None:
            return None
        return self._exporter_manager.export(self._last_result, path)

    def _make_field(self, parameter: Any) -> QWidget:
        if parameter.kind is ToolParameterKind.INTEGER:
            spin = QSpinBox(self)
            spin.setMinimum(parameter.minimum if parameter.minimum is not None else 0)
            spin.setMaximum(parameter.maximum if parameter.maximum is not None else 2_000_000_000)
            default = parameter.default if isinstance(parameter.default, int) else spin.minimum()
            spin.setValue(max(spin.minimum(), min(spin.maximum(), default)))
            return spin
        if parameter.kind is ToolParameterKind.CHOICE:
            combo = QComboBox(self)
            for index, choice in enumerate(parameter.choices):
                label = (
                    parameter.choice_labels[index]
                    if index < len(parameter.choice_labels)
                    else choice
                )
                combo.addItem(label, choice)
            if parameter.default in parameter.choices:
                combo.setCurrentIndex(combo.findData(parameter.default))
            return combo
        if parameter.kind is ToolParameterKind.FILE:
            return _FileInput(placeholder=parameter.placeholder, parent=self)
        field = CommandInput(
            label="",
            placeholder=parameter.placeholder,
            mode=(
                CommandInput.MODE_MULTI
                if parameter.kind is ToolParameterKind.MULTILINE
                else CommandInput.MODE_SINGLE
            ),
            parent=self,
        )
        if isinstance(parameter.default, str):
            field.set_text(parameter.default)
        return field

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        """Accept dropped local files; they are analyzed, never executed."""
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            file_path = url.toLocalFile()
            for widget in self._fields.values():
                if isinstance(widget, _FileInput):
                    widget.set_text(file_path)
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

    def _connect_field_changes(self, widget: QWidget) -> None:
        if isinstance(widget, CommandInput):
            widget.text_changed.connect(self._on_field_changed)
        elif isinstance(widget, QSpinBox):
            widget.valueChanged.connect(self._on_field_changed)
        elif isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(self._on_field_changed)
        elif isinstance(widget, _FileInput):
            widget.text_changed.connect(self._on_field_changed)

    def _on_field_changed(self, *_args: object) -> None:
        self._update_visibility()

    def _update_visibility(self) -> None:
        """Show/hide form rows declared through ``visible_when`` conditions."""
        if self._form is None:
            return
        values = self.params()
        for parameter, row in self._row_meta:
            if not parameter.visible_when:
                continue
            visible = all(
                values.get(field) == expected for field, expected in parameter.visible_when.items()
            )
            self._form.setRowVisible(row, visible)

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
        self._progress_label.setText("等待执行…")
        self._progress_label.setVisible(True)
        self.set_running(True)

    def _cancel(self) -> None:
        if self._task_manager is not None and self._current_task_id is not None:
            self._task_manager.cancel(self._current_task_id)
            self._progress_label.setText("正在取消…")

    def _on_task_updated(self, task: Task) -> None:
        if self._current_task_id is None or task.task_id != self._current_task_id:
            return
        self._progress_label.setText(task.message or f"进度 {task.progress:.0f}%")

    def _on_task_finished(self, task: Task) -> None:
        if self._current_task_id is None or task.task_id != self._current_task_id:
            return
        self.set_running(False)
        result = task.result
        if result is None:
            message = task.message or "任务未返回结果。"
            self._result_panel.show_error(message)
            self._mark_validation("invalid", message)
            return
        self._last_result = result
        self._result_panel.show_result(result)
        if result.is_ok:
            self._mark_validation("valid", "")
        else:
            self._mark_validation("invalid", result.summary)

    def _mark_validation(self, state: str | None, message: str) -> None:
        for widget in self._fields.values():
            if isinstance(widget, CommandInput):
                widget.set_validation(state, message)

    def _copy_result(self) -> None:
        if self._last_result is not None:
            self._result_panel.copy_to_clipboard()

    def _show_send_to_menu(self) -> None:
        if self._last_result is None:
            return
        menu = QMenu(self)
        text = self._result_panel.current_text()
        for tool_id, label in self.SEND_TO_TARGETS:
            action = menu.addAction(f"发送到 {label}")
            action.triggered.connect(
                lambda _checked=False, target=tool_id, payload=text: self.send_to_requested.emit(
                    target, payload
                )
            )
        menu.exec(self._send_to_button.mapToGlobal(QPoint(0, self._send_to_button.height())))

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
            exported = self.export_result(Path(file_path))
            self._logger.info("结果已导出：%s", exported)
        except ExportError as exc:
            self._result_panel.show_error(exc.user_message)

    def _show_row_detail(self, row: dict[str, Any]) -> None:
        self._detail_view.setPlainText(json.dumps(row, ensure_ascii=False, indent=2))
        self._detail_view.setVisible(True)

    def _clear(self) -> None:
        for widget in self._fields.values():
            if isinstance(widget, CommandInput):
                widget.clear()
            elif isinstance(widget, QSpinBox):
                widget.setValue(widget.minimum())
            elif isinstance(widget, QComboBox) and widget.count() > 0:
                widget.setCurrentIndex(0)
            elif isinstance(widget, _FileInput):
                widget.clear()
        self._detail_view.setVisible(False)
        self._result_panel.clear()
