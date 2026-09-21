"""PE analysis against a real system PE and corrupt inputs."""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

import pytest

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.file_analysis.pe_analysis import PeAnalysisTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-fpe",
        tool_id="file_analysis.pe_analysis",
        logger=logging.getLogger("tests.fpe"),
        cancel_event=threading.Event(),
    )


@pytest.fixture
def notepad() -> Path | None:
    system_root = Path(os.environ.get("SYSTEMROOT", r"C:\Windows"))
    candidate = system_root / "System32" / "notepad.exe"
    return candidate if candidate.is_file() else None


def test_analyze_real_pe(notepad: Path | None) -> None:
    if notepad is None:
        pytest.skip("notepad.exe not available")
    result = PeAnalysisTool().run({"file_path": str(notepad)}, _context())
    assert result.status is ResultStatus.SUCCESS
    rows = {(row["section"], row["item"]): row["value"] for row in result.data}
    assert ("基本信息", "架构") in rows
    assert any(section.startswith("Section:") for section, _item in rows)
    assert any(section.startswith("Import:") for section, _item in rows)
    assert ("Overlay", "大小") in rows


def test_not_a_pe(tmp_path: Path) -> None:
    path = tmp_path / "not_pe.bin"
    path.write_bytes(b"just text")
    result = PeAnalysisTool().run({"file_path": str(path)}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == "该文件不是有效的PE文件。"


def test_truncated_pe(tmp_path: Path) -> None:
    path = tmp_path / "truncated.exe"
    path.write_bytes(b"MZ\x90\x00" + b"\x00" * 32)
    result = PeAnalysisTool().run({"file_path": str(path)}, _context())
    assert result.status is ResultStatus.FAILED
    assert "PE" in result.summary


def test_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    result = PeAnalysisTool().run({"file_path": str(path)}, _context())
    assert result.status is ResultStatus.FAILED
