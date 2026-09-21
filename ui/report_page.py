"""Report center page: list, editor, preview and export."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from core.reports.report import Report
from core.reports.report_manager import ReportManager

TEMPLATES = ("basic", "web_security", "file_analysis", "system_security", "ctf")


class ReportPage(QWidget):
    """Lists reports and provides a simple Markdown-ish editor plus preview."""

    def __init__(self, report_manager: ReportManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._manager = report_manager
        self._reports: list[Report] = []
        self._current: Report | None = None

        title = QLabel("报告中心", self)
        title.setObjectName("pageTitle")
        self._table = QTableWidget(0, 5, self)
        self._table.setHorizontalHeaderLabels(("标题", "作者", "更新", "任务数", "模板"))
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.itemSelectionChanged.connect(self._on_select)

        self._title_edit = QLineEdit(self)
        self._title_edit.setPlaceholderText("报告标题")
        self._description_edit = QLineEdit(self)
        self._description_edit.setPlaceholderText("描述")
        self._author_edit = QLineEdit(self)
        self._author_edit.setPlaceholderText("作者")
        self._project_edit = QLineEdit(self)
        self._project_edit.setPlaceholderText("项目")
        self._tags_edit = QLineEdit(self)
        self._tags_edit.setPlaceholderText("标签（逗号分隔）")
        self._template_combo = QComboBox(self)
        self._template_combo.addItems(TEMPLATES)
        form = QFormLayout()
        form.addRow("标题", self._title_edit)
        form.addRow("描述", self._description_edit)
        form.addRow("作者", self._author_edit)
        form.addRow("项目", self._project_edit)
        form.addRow("标签", self._tags_edit)
        form.addRow("模板", self._template_combo)

        self._section_combo = QComboBox(self)
        self._notes_edit = QPlainTextEdit(self)
        self._notes_edit.setPlaceholderText("当前 Section 的说明（Markdown）")
        self._conclusion_edit = QPlainTextEdit(self)
        self._conclusion_edit.setPlaceholderText("结论")
        self._tasks_table = QTableWidget(0, 2, self)
        self._tasks_table.setHorizontalHeaderLabels(("任务", "Section"))
        self._tasks_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tasks_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._preview = QTextBrowser(self)

        new_button = QPushButton("新建", self)
        save_button = QPushButton("保存", self)
        add_task_button = QPushButton("添加任务", self)
        remove_task_button = QPushButton("移除任务", self)
        export_button = QPushButton("导出", self)
        delete_button = QPushButton("删除报告", self)
        for button in (
            new_button,
            save_button,
            add_task_button,
            remove_task_button,
            export_button,
            delete_button,
        ):
            button.setObjectName("flatButton")
        new_button.clicked.connect(self._create)
        save_button.clicked.connect(self._save)
        add_task_button.clicked.connect(self._add_task)
        remove_task_button.clicked.connect(self._remove_task)
        export_button.clicked.connect(self._export)
        delete_button.clicked.connect(self._delete)
        self._section_combo.currentIndexChanged.connect(self._on_section_changed)
        self._notes_edit.textChanged.connect(self._sync_section_note)

        actions = QHBoxLayout()
        for button in (
            new_button,
            save_button,
            add_task_button,
            remove_task_button,
            export_button,
            delete_button,
        ):
            actions.addWidget(button)
        actions.addStretch(1)

        editor = QVBoxLayout()
        editor.addLayout(form)
        editor.addWidget(QLabel("Section 说明", self))
        editor.addWidget(self._section_combo)
        editor.addWidget(self._notes_edit)
        editor.addWidget(QLabel("结论", self))
        editor.addWidget(self._conclusion_edit)
        editor.addWidget(self._tasks_table)

        body = QHBoxLayout()
        body.addLayout(editor, 3)
        body.addWidget(self._preview, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addLayout(actions)
        layout.addWidget(self._table, 1)
        layout.addLayout(body, 3)
        self.refresh()

    def refresh(self) -> None:
        reports, task_counts = self._manager.list()
        self._reports = reports
        self._table.setRowCount(len(reports))
        for row, report in enumerate(reports):
            values = (
                report.title,
                report.author or "-",
                report.updated_at[:16],
                str(task_counts.get(report.report_id, 0)),
                report.template,
            )
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(str(value)))
        if self._current is None and reports:
            self._table.setCurrentCell(0, 0)

    def _on_select(self) -> None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._reports):
            return
        self._current = self._reports[row]
        self._load_editor()

    def _load_editor(self) -> None:
        if self._current is None:
            return
        self._title_edit.setText(self._current.title)
        self._description_edit.setText(self._current.description)
        self._author_edit.setText(self._current.author)
        self._project_edit.setText(self._current.project)
        self._tags_edit.setText(", ".join(self._current.tags))
        self._template_combo.setCurrentIndex(
            max(0, self._template_combo.findText(self._current.template))
        )
        keys = list(self._current.sections)
        self._section_combo.clear()
        self._section_combo.addItems(keys)
        self._conclusion_edit.setPlainText(self._current.conclusion)
        self._load_section_note()
        self._load_task_rows()
        self._update_preview()

    def _load_section_note(self) -> None:
        if self._current is None:
            return
        key = self._section_combo.currentText()
        self._notes_edit.blockSignals(True)
        self._notes_edit.setPlainText(self._current.sections.get(key, ""))
        self._notes_edit.blockSignals(False)

    def _on_section_changed(self) -> None:
        self._load_section_note()

    def _sync_section_note(self) -> None:
        if self._current is not None:
            key = self._section_combo.currentText()
            if key:
                self._current.sections[key] = self._notes_edit.toPlainText()

    def _load_task_rows(self) -> None:
        if self._current is None:
            return
        refs = self._current.task_refs
        self._tasks_table.setRowCount(len(refs))
        for row, ref in enumerate(refs):
            self._tasks_table.setItem(row, 0, QTableWidgetItem(ref.task_id))
            self._tasks_table.setItem(row, 1, QTableWidgetItem(ref.section))

    def _create(self) -> None:
        report = self._manager.create(
            self._title_edit.text().strip() or "未命名报告",
            description=self._description_edit.text().strip(),
            author=self._author_edit.text().strip(),
            project=self._project_edit.text().strip(),
            template=self._template_combo.currentText(),
        )
        self._current = report
        self.refresh()
        self._load_editor()

    def _save(self) -> None:
        if self._current is None:
            return
        self._sync_section_note()
        self._current.title = self._title_edit.text().strip() or self._current.title
        self._current.description = self._description_edit.text().strip()
        self._current.author = self._author_edit.text().strip()
        self._current.project = self._project_edit.text().strip()
        self._current.tags = [
            tag.strip() for tag in self._tags_edit.text().split(",") if tag.strip()
        ]
        self._current.template = self._template_combo.currentText()
        self._current.conclusion = self._conclusion_edit.toPlainText()
        self._manager.save(self._current)
        self.refresh()
        self._update_preview()

    def _add_task(self) -> None:
        if self._current is None:
            return
        task_id, ok = QInputDialog.getText(self, "添加任务", "任务 ID：")
        if not ok or not task_id.strip():
            return
        section = self._section_combo.currentText() or "Findings"
        updated = self._manager.add_task(self._current.report_id, task_id.strip(), section)
        if updated is None:
            QMessageBox.warning(self, "添加任务", "任务不存在于历史中。")
            return
        self._current = updated
        self._load_task_rows()
        self._update_preview()

    def _remove_task(self) -> None:
        if self._current is None:
            return
        row = self._tasks_table.currentRow()
        if row < 0 or row >= len(self._current.task_refs):
            return
        task_id = self._current.task_refs[row].task_id
        updated = self._manager.remove_task(self._current.report_id, task_id)
        if updated is not None:
            self._current = updated
            self._load_task_rows()
            self._update_preview()

    def _update_preview(self) -> None:
        if self._current is None:
            return
        markdown = self._manager.render_markdown(self._current.report_id)
        self._preview.setPlainText(markdown or "")

    def _export(self) -> None:
        if self._current is None:
            return
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "导出报告",
            f"report_{self._current.title}",
            "Markdown (*.md);;JSON (*.json);;文本 (*.txt)",
        )
        if path:
            self._manager.export(self._current.report_id, Path(path))

    def _delete(self) -> None:
        if self._current is None:
            return
        if (
            QMessageBox.question(
                self,
                "删除报告",
                f"确认删除报告「{self._current.title}」？（不会删除引用的任务）",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self._manager.delete(self._current.report_id)
        self._current = None
        self.refresh()
