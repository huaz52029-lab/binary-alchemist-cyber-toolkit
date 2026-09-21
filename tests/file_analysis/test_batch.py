"""Batch file analysis: success, per-file errors and cancellation."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from core.result import ResultStatus
from core.task import ExecutionContext, TaskStatus
from core.task_manager import TaskManager
from modules.file_analysis.batch import BatchAnalysisTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-fbatch",
        tool_id="file_analysis.batch",
        logger=logging.getLogger("tests.fbatch"),
        cancel_event=threading.Event(),
    )


def test_batch_over_directory(tmp_path: Path) -> None:
    directory = tmp_path / "samples"
    directory.mkdir()
    for index in range(6):
        (directory / f"sample{index}.txt").write_bytes(
            f"content {index} https://example.com/{index}".encode()
        )
    result = BatchAnalysisTool().run(
        {"paths": str(directory), "recursive": "no", "max_files": 20},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert len(result.data) == 6
    assert all(row["status"] == "成功" for row in result.data)
    assert all(row["type"] == "Text" for row in result.data)
    assert "成功 6" in result.summary


def test_batch_partial_failures(tmp_path: Path) -> None:
    good = tmp_path / "good.txt"
    good.write_bytes(b"ok")
    paths = f"{good}\n{tmp_path / 'missing.bin'}\n{tmp_path}"
    result = BatchAnalysisTool().run(
        {"paths": paths, "recursive": "no", "max_files": 20},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    statuses = [row["status"] for row in result.data]
    assert statuses.count("成功") >= 1
    assert "失败" in statuses
    assert any(finding.title == "部分文件分析失败" for finding in result.findings)


def test_batch_recursive(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_bytes(b"a")
    (root / "sub" / "b.txt").write_bytes(b"b")
    result = BatchAnalysisTool().run(
        {"paths": str(root), "recursive": "yes", "max_files": 20},
        _context(),
    )
    assert len(result.data) == 2


def test_batch_file_limit(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    for index in range(10):
        (root / f"{index}.txt").write_bytes(b"x")
    result = BatchAnalysisTool().run(
        {"paths": str(root), "recursive": "no", "max_files": 5},
        _context(),
    )
    assert len(result.data) == 5


def test_batch_cancellation(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    for index in range(200):
        (root / f"{index}.txt").write_bytes((f"content-{index}" * 500).encode())
    manager = TaskManager(max_workers=2)
    try:
        task_id = manager.submit_tool(
            BatchAnalysisTool(),
            {"paths": str(root), "recursive": "no", "max_files": 200},
        )
        time.sleep(0.15)
        manager.cancel(task_id)
        snapshot = manager.wait(task_id, timeout=20.0)
        assert snapshot.status is TaskStatus.CANCELLED
    finally:
        manager.shutdown(wait=True)
