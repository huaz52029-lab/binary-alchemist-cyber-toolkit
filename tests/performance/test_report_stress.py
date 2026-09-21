"""Report stress: 100 reports, 10 referenced tasks each."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from core.history.task_history import TaskHistoryManager
from core.reports.report_manager import ReportManager
from core.reports.report_repository import ReportRepository
from core.result import ResultStatus, ToolResult
from core.task import Task, TaskStatus


def _task(task_id: str) -> Task:
    now = datetime.now(UTC)
    task = Task(task_id=task_id, tool_id="web.security_headers", params={})
    task.status = TaskStatus.COMPLETED
    task.started_at = now
    task.finished_at = now
    task.result = ToolResult(status=ResultStatus.SUCCESS, summary="ok")
    return task


def test_100_reports_lifecycle(tmp_path: Path) -> None:
    history = TaskHistoryManager(tmp_path / "toolkit.db", tmp_path / "results")
    reports = ReportManager(ReportRepository(tmp_path / "toolkit.db"), history)
    for index in range(100):
        report = reports.create(f"报告 {index:03d}", template="basic", project=f"p{index % 5}")
        for item in range(10):
            task_id = f"t-{index:03d}-{item}"
            history.record_task(_task(task_id))
            reports.add_task(report.report_id, task_id, "findings")
    listed, counts = reports.list()
    assert len(listed) == 100
    assert all(counts[report.report_id] == 10 for report in listed)
    searched, _counts = reports.list(search="报告 007")
    assert len(searched) == 1
    target = reports.get(searched[0].report_id)
    assert target is not None
    markdown = reports.render_markdown(target.report_id)
    assert markdown is not None
    assert "10 个分析任务" in markdown
    export_path = tmp_path / "exported.md"
    reports.export(target.report_id, export_path)
    assert export_path.read_text(encoding="utf-8").startswith("# 报告 007")
    reports.delete(target.report_id)
    assert reports.get(target.report_id) is None
    assert history.get("t-007-0") is not None, "deleting a report must keep tasks"
    history.close()
    reports.close()
