"""File info metadata and type mismatch findings."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.file_analysis.file_info import FileInfoTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-finfo",
        tool_id="file_analysis.file_info",
        logger=logging.getLogger("tests.finfo"),
        cancel_event=threading.Event(),
    )


def test_text_file_info(tmp_path: Path) -> None:
    path = tmp_path / "hello.txt"
    path.write_bytes(b"hello world")
    result = FileInfoTool().run({"file_path": str(path)}, _context())
    assert result.status is ResultStatus.SUCCESS
    row = result.data[0]
    assert row["name"] == "hello.txt"
    assert row["detected_type"] == "Text"
    assert row["extension"] == ".txt"
    assert row["size"].endswith("字节）")
    assert result.findings == []


def test_extension_mismatch_finding(tmp_path: Path) -> None:
    path = tmp_path / "fake.txt"
    path.write_bytes(b"MZ\x90\x00" + b"\x00" * 64)
    result = FileInfoTool().run({"file_path": str(path)}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["detected_type"] == "PE"
    assert any(f.title == "文件扩展名与文件实际结构不一致" for f in result.findings)


def test_missing_file(tmp_path: Path) -> None:
    result = FileInfoTool().run({"file_path": str(tmp_path / "nope.bin")}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == "文件不存在。"


def test_directory_rejected(tmp_path: Path) -> None:
    result = FileInfoTool().run({"file_path": str(tmp_path)}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == "文件不存在。"
