from __future__ import annotations

from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from ui.widgets.command_input import CommandInput
from ui.widgets.log_viewer import LogViewer
from ui.widgets.result_table import ResultTable
from ui.widgets.status_card import StatusCard


def test_status_card_value_and_click(qapp: QApplication) -> None:
    card = StatusCard(title="工具数量", value="0", description="已注册工具")
    assert card.value() == "0"
    card.set_value(5)
    assert card.value() == "5"
    spy = QSignalSpy(card.clicked)
    card.clicked.emit()
    assert spy.count() == 1


def test_result_table_columns_rows_sort_and_copy(qapp: QApplication) -> None:
    table = ResultTable()
    table.set_columns(["host", "port"])
    table.set_rows([["127.0.0.1", "80"], ["10.0.0.1", "22"]])
    assert table.row_count() == 2
    table._model.sort(1)
    table._copy_all()
    clipboard = QApplication.clipboard().text()
    assert "127.0.0.1" in clipboard
    table.set_from_dicts([{"a": 1, "b": 2}])
    assert table.row_count() == 1
    table.clear()
    assert table.row_count() == 0


def test_command_input_single_and_multi(qapp: QApplication) -> None:
    single = CommandInput(label="目标", placeholder="example.com")
    spy = QSignalSpy(single.text_changed)
    single.set_text("example.com")
    assert single.text() == "example.com"
    assert spy.count() == 1
    single.set_validation("invalid", "请输入有效的目标")
    assert single.editor().property("validation") == "invalid"
    multi = CommandInput(mode=CommandInput.MODE_MULTI)
    multi.set_text("line1\nline2")
    assert multi.text() == "line1\nline2"
    multi.clear()
    assert multi.text() == ""


def test_log_viewer_append_clear_and_trim(qapp: QApplication) -> None:
    viewer = LogViewer(max_lines=5)
    viewer.append_log("INFO", "hello <world>")
    assert "hello <world>" in viewer.toPlainText()
    for index in range(10):
        viewer.append_log("DEBUG", f"line {index}")
    assert viewer.blockCount() <= 6
    viewer.set_auto_scroll(False)
    assert not viewer.auto_scroll()
    viewer.clear_logs()
    assert viewer.toPlainText() == ""
