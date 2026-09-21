"""Streaming strings extraction across encodings."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.file_analysis.strings import FileStringsTool, extract_strings, keyword_hints


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-fstr",
        tool_id="file_analysis.strings",
        logger=logging.getLogger("tests.fstr"),
        cancel_event=threading.Event(),
    )


def test_ascii_offsets(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"\x00\x01hello\x00world\x00\xff\xfe")
    records = extract_strings(path, encoding="ascii", min_length=4)
    texts = {record.text: record.offset for record in records}
    assert texts == {"hello": 2, "world": 8}
    assert all(record.encoding == "ASCII" for record in records)


def test_utf8_extraction(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"\x00\x01" + "你好世界".encode() + b"\x00")
    records = extract_strings(path, encoding="utf8", min_length=3)
    assert any(record.text == "你好世界" and record.offset == 2 for record in records)


def test_utf16le_extraction(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"\x00\x00" + "hello".encode("utf-16-le") + b"\x00\x00")
    records = extract_strings(path, encoding="utf16le", min_length=4)
    assert any(record.text == "hello" and record.offset == 2 for record in records)
    assert all(record.encoding == "UTF-16LE" for record in records)


def test_min_length_respected(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"abc\x00longer-string")
    records = extract_strings(path, encoding="ascii", min_length=8)
    assert [record.text for record in records] == ["longer-string"]


def test_tool_rows_and_hints(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"powershell -enc abc  https://example.com")
    result = FileStringsTool().run({"file_path": str(path)}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert any("powershell" in row["text"] for row in result.data)
    assert any(row["hints"] != "-" for row in result.data)
    assert result.findings[0].title == "发现分析线索字符串"


def test_keyword_hints() -> None:
    assert keyword_hints("call CreateProcessA") == ["CreateProcess"]
    assert keyword_hints("plain") == []
