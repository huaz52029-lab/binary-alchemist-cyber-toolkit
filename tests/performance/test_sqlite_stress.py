"""SQLite stress: concurrent writers, 10k history rows, multi-connection integrity."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from pathlib import Path

from core.history.task_history import TaskHistoryManager
from core.reports.report_manager import ReportManager
from core.reports.report_repository import ReportRepository
from core.result import ResultStatus, ToolResult
from core.task import Task, TaskStatus


def _task(task_id: str, status: TaskStatus = TaskStatus.COMPLETED) -> Task:
    now = datetime.now(UTC)
    task = Task(task_id=task_id, tool_id="crypto.hash", params={})
    task.status = status
    task.started_at = now
    task.finished_at = now
    task.result = ToolResult(status=ResultStatus.SUCCESS, summary=f"ok {task_id}")
    return task


def test_concurrent_history_writes_do_not_lock_or_lose_rows(tmp_path: Path) -> None:
    manager = TaskHistoryManager(tmp_path / "toolkit.db", tmp_path / "results")
    errors: list[BaseException] = []
    threads = 16
    per_thread = 50

    def writer(thread_index: int) -> None:
        try:
            for item in range(per_thread):
                manager.record_task(_task(f"t-{thread_index:02d}-{item:03d}"))
        except BaseException as exc:
            errors.append(exc)

    workers = [threading.Thread(target=writer, args=(index,)) for index in range(threads)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=60)
    assert not errors
    rows, total = manager.query(limit=1000)
    assert total == threads * per_thread
    assert len(rows) == threads * per_thread
    manager.close()


def test_history_10k_pagination_search_filter_sort(tmp_path: Path) -> None:
    manager = TaskHistoryManager(tmp_path / "toolkit.db", tmp_path / "results")
    for index in range(10000):
        manager.record_task(
            _task(f"t-{index:05d}")
            if index % 2 == 0
            else Task(
                task_id=f"t-{index:05d}",
                tool_id="network.ping",
                params={},
                status=TaskStatus.FAILED,
                message="unreachable",
            )
        )
    rows, total = manager.query(limit=50, offset=0)
    assert total == 10000
    assert len(rows) == 50
    page, _total = manager.query(limit=50, offset=9950)
    assert len(page) == 50
    matched, matched_total = manager.query(search="t-00042")
    assert matched_total >= 1
    assert matched[0]["task_id"] == "t-00042"
    _failed, failed_total = manager.query(status="FAILED")
    assert failed_total == 5000
    _ping, ping_total = manager.query(tool_id="network.ping")
    assert ping_total == 5000
    ascending, _total = manager.query(order_by="created_at", order_desc=False, limit=5)
    assert ascending[0]["task_id"] == "t-00000"
    manager.close()


def test_history_and_reports_share_one_wal_database(tmp_path: Path) -> None:
    db = tmp_path / "toolkit.db"
    history = TaskHistoryManager(db, tmp_path / "results")
    reports = ReportManager(ReportRepository(db), history)
    history.record_task(_task("t-shared"))
    report = reports.create("共享库报告", template="basic")
    reports.add_task(report.report_id, "t-shared", "findings")
    markdown = reports.render_markdown(report.report_id)
    assert markdown is not None
    assert "crypto.hash" in markdown
    assert reports.get(report.report_id) is not None
    history.close()
    reports.close()
