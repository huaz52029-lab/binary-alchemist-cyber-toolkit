"""Composite file analysis."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.file_analysis.analyzer import FileAnalyzerTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-fana",
        tool_id="file_analysis.analyzer",
        logger=logging.getLogger("tests.fana"),
        cancel_event=threading.Event(),
    )


def test_analyze_text_file(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_bytes(b"hello world https://example.com 192.168.1.1")
    result = FileAnalyzerTool().run({"file_path": str(path)}, _context())
    assert result.status is ResultStatus.SUCCESS
    sections = {row["section"] for row in result.data}
    assert {"文件", "类型", "Hash", "Strings", "Entropy", "IOC"} <= sections
    assert any(finding.title == "发现候选 IOC" for finding in result.findings)
    assert any(finding.title == "静态分析说明" for finding in result.findings)
    assert "静态分析" in result.summary


def test_analyze_pe_file(tmp_path: Path) -> None:
    import os

    system_root = Path(os.environ.get("SYSTEMROOT", r"C:\Windows"))
    notepad = system_root / "System32" / "notepad.exe"
    if not notepad.is_file():
        return
    result = FileAnalyzerTool().run({"file_path": str(notepad)}, _context())
    assert result.status is ResultStatus.SUCCESS
    sections = {row["section"] for row in result.data}
    assert "基本信息" in sections or any(s.startswith("Section:") for s in sections)


def test_missing_file(tmp_path: Path) -> None:
    result = FileAnalyzerTool().run({"file_path": str(tmp_path / "nope")}, _context())
    assert result.status is ResultStatus.FAILED
