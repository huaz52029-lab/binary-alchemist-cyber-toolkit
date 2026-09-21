"""File hash tool against fixed content."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.file_analysis.hashes import FileHashesTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-fhash",
        tool_id="file_analysis.hashes",
        logger=logging.getLogger("tests.fhash"),
        cancel_event=threading.Event(),
    )


def test_known_file_hashes(tmp_path: Path) -> None:
    path = tmp_path / "hello.bin"
    path.write_bytes(b"hello")
    result = FileHashesTool().run({"file_path": str(path)}, _context())
    assert result.status is ResultStatus.SUCCESS
    row = result.data[0]
    assert row["md5"] == "5d41402abc4b2a76b9719d911017c592"
    assert row["sha1"] == "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"
    assert row["sha256"].startswith("2cf24dba5f")
    assert row["sha512"].startswith("9b71d224bd62f378")


def test_empty_file_hashes(tmp_path: Path) -> None:
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    result = FileHashesTool().run({"file_path": str(path)}, _context())
    assert result.data[0]["md5"] == "d41d8cd98f00b204e9800998ecf8427e"


def test_missing_file(tmp_path: Path) -> None:
    result = FileHashesTool().run({"file_path": str(tmp_path / "nope")}, _context())
    assert result.status is ResultStatus.FAILED
