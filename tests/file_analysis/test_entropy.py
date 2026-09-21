"""Shannon entropy values and tool behavior."""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

import pytest

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.file_analysis.entropy import FileEntropyTool, shannon_entropy
from modules.file_analysis.entropy.analyzer import entropy_from_bytes


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-fent",
        tool_id="file_analysis.entropy",
        logger=logging.getLogger("tests.fent"),
        cancel_event=threading.Event(),
    )


def test_entropy_zero_data() -> None:
    assert shannon_entropy([100, 0, 0], 100) == 0.0


def test_entropy_uniform_random() -> None:
    assert entropy_from_bytes(bytes(range(256))) == pytest.approx(8.0)


def test_entropy_text_lower() -> None:
    text_entropy = entropy_from_bytes(b"hello world, plain text")
    assert 0.0 < text_entropy < 7.0


def test_tool_on_zeros_file(tmp_path: Path) -> None:
    path = tmp_path / "zeros.bin"
    path.write_bytes(b"\x00" * 1024)
    result = FileEntropyTool().run({"file_path": str(path)}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["entropy"] == 0.0


def test_tool_high_entropy_finding(tmp_path: Path) -> None:
    path = tmp_path / "random.bin"
    path.write_bytes(os.urandom(4096))
    result = FileEntropyTool().run({"file_path": str(path)}, _context())
    assert any(finding.title == "文件整体熵较高" for finding in result.findings)
