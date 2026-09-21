"""Hex viewer: paged dumps, offset jump and search."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.file_analysis.hex_viewer import FileHexViewerTool, hexdump_lines


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-fhex",
        tool_id="file_analysis.hex_viewer",
        logger=logging.getLogger("tests.fhex"),
        cancel_event=threading.Event(),
    )


def test_hexdump_lines() -> None:
    rows = hexdump_lines(b"MZ\x90\x00hello", 0x1000)
    assert rows[0]["offset"] == "00001000"
    assert rows[0]["hex"] == "4D 5A 90 00 68 65 6C 6C 6F"
    assert rows[0]["ascii"] == "MZ..hello"


def test_offset_jump(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"0123456789abcdef" * 8)
    result = FileHexViewerTool().run(
        {"file_path": str(path), "offset": "0x10", "length": 16},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["offset"] == "00000010"
    assert result.data[0]["ascii"] == "0123456789abcdef"


def test_ascii_search(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"prefix-MZ-suffixMZ")
    result = FileHexViewerTool().run(
        {"file_path": str(path), "search": "MZ", "search_mode": "ascii"},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert len(result.data) == 2
    assert all("4D 5A" in row["hex"] for row in result.data)


def test_hex_search(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"\x01\x02" + b"target" + b"\xff")
    result = FileHexViewerTool().run(
        {"file_path": str(path), "search": "74 61 72", "search_mode": "hex"},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["offset"] == "00000002"


def test_search_no_match(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"nothing here")
    result = FileHexViewerTool().run(
        {"file_path": str(path), "search": "zzz", "search_mode": "ascii"},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert result.summary == "未找到匹配。"


def test_invalid_offset(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"x")
    result = FileHexViewerTool().run(
        {"file_path": str(path), "offset": "zz"},
        _context(),
    )
    assert result.status is ResultStatus.FAILED
    assert "偏移量无效" in result.summary
