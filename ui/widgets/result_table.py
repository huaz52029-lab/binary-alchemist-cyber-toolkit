"""Reusable sortable/selectable table with clipboard support."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QHeaderView,
    QMenu,
    QTableView,
    QVBoxLayout,
    QWidget,
)


def _sort_key(value: Any) -> tuple[int, Any]:
    if value is None:
        return (3, "")
    if isinstance(value, (int, float)):
        return (0, value)
    return (1, str(value))


_EMPTY_INDEX = QModelIndex()


class _ResultTableModel(QAbstractTableModel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._columns: list[str] = []
        self._rows: list[list[Any]] = []

    def set_columns(self, columns: Sequence[str]) -> None:
        self.beginResetModel()
        self._columns = list(columns)
        self.endResetModel()

    def set_rows(self, rows: Sequence[Sequence[Any]]) -> None:
        self.beginResetModel()
        self._rows = [list(row) for row in rows]
        self.endResetModel()

    def clear(self) -> None:
        self.set_rows([])

    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = _EMPTY_INDEX,
    ) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = _EMPTY_INDEX,
    ) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = int(Qt.ItemDataRole.DisplayRole),
    ) -> Any:
        if not index.isValid() or role not in (
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.EditRole,
        ):
            return None
        row = self._rows[index.row()]
        return row[index.column()] if index.column() < len(row) else None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = int(Qt.ItemDataRole.DisplayRole),
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation is Qt.Orientation.Horizontal:
            return self._columns[section] if section < len(self._columns) else ""
        return section + 1

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        if not self._rows or column >= len(self._columns):
            return
        self.layoutAboutToBeChanged.emit()
        self._rows.sort(
            key=lambda row: _sort_key(row[column] if column < len(row) else None),
            reverse=order is Qt.SortOrder.DescendingOrder,
        )
        self.layoutChanged.emit()


class ResultTable(QWidget):
    """Tabular result view: columns, sorting, selection and clipboard export."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = _ResultTableModel(self)
        self._view = QTableView(self)
        self._view.setModel(self._model)
        self._view.setSortingEnabled(True)
        self._view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._view.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self._view.setAlternatingRowColors(True)
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._show_context_menu)
        header = self._view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

    def set_columns(self, columns: Sequence[str]) -> None:
        self._model.set_columns(columns)

    def set_rows(self, rows: Sequence[Sequence[Any]]) -> None:
        self._model.set_rows(rows)

    def set_from_dicts(self, records: Sequence[Mapping[str, Any]]) -> None:
        """Convenience: derive columns from dict keys (first-seen order)."""
        columns: list[str] = []
        for record in records:
            for key in record:
                if key not in columns:
                    columns.append(key)
        rows = [[record.get(column) for column in columns] for record in records]
        self.set_columns(columns)
        self.set_rows(rows)

    def clear(self) -> None:
        self._model.clear()

    def row_count(self) -> int:
        return self._model.rowCount()

    def to_text(self) -> str:
        """Render the table as TSV text (header + rows) for clipboard use."""
        columns = self._model._columns
        rows = [
            [self._model.index(row, column).data() for column in range(self._model.columnCount())]
            for row in range(self._model.rowCount())
        ]
        lines = ["\t".join(columns)]
        lines.extend("\t".join("" if cell is None else str(cell) for cell in row) for row in rows)
        return "\n".join(lines)

    def selected_rows(self) -> list[list[Any]]:
        rows: list[list[Any]] = []
        for index in self._view.selectionModel().selectedRows():
            row = index.row()
            rows.append(
                [
                    self._model.index(row, column).data()
                    for column in range(self._model.columnCount())
                ]
            )
        return rows

    def _show_context_menu(self, position: Any) -> None:
        menu = QMenu(self)
        copy_selected = QAction("复制选中行", menu)
        copy_all = QAction("复制全部", menu)
        clear_action = QAction("清空", menu)
        copy_selected.triggered.connect(self._copy_selected)
        copy_all.triggered.connect(self._copy_all)
        clear_action.triggered.connect(self.clear)
        menu.addAction(copy_selected)
        menu.addAction(copy_all)
        menu.addSeparator()
        menu.addAction(clear_action)
        menu.exec(self._view.viewport().mapToGlobal(position))

    def _copy_selected(self) -> None:
        self._copy_rows(self.selected_rows())

    def _copy_all(self) -> None:
        rows = [
            [self._model.index(row, column).data() for column in range(self._model.columnCount())]
            for row in range(self._model.rowCount())
        ]
        self._copy_rows(rows)

    @staticmethod
    def _copy_rows(rows: list[list[Any]]) -> None:
        if not rows:
            return
        text = "\n".join(
            "\t".join("" if cell is None else str(cell) for cell in row) for row in rows
        )
        QApplication.clipboard().setText(text)
