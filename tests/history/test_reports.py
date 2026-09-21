"""Report model, manager, renderer and export."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from core.finding import Finding, Severity
from core.history.task_history import TaskHistoryManager
from core.reports.report_manager import ReportManager
from core.reports.report_repository import ReportRepository
from core.result import ResultStatus, ToolResult
from core.task import Task, TaskStatus


def _record_task(manager: TaskHistoryManager, task_id: str, summary: str) -> None:
    now = datetime.now(UTC)
    task = Task(task_id=task_id, tool_id="web.security_headers", params={})
    task.status = TaskStatus.COMPLETED
    task.started_at = now
    task.finished_at = now
    task.result = ToolResult(
        status=ResultStatus.SUCCESS,
        summary=summary,
        findings=[
            Finding(
                title="缺少 Content-Security-Policy",
                severity=Severity.LOW,
                description="响应中未检测到 CSP。",
                source="web.security_headers",
            ),
            Finding(
                title="证书已过期",
                severity=Severity.HIGH,
                description="证书已过期。",
                source="web.tls_info",
            ),
        ],
    )
    manager.record_task(task)


def _setup(tmp_path: Path) -> tuple[TaskHistoryManager, ReportManager]:
    history = TaskHistoryManager(
        tmp_path / "toolkit.db",
        tmp_path / "results",
    )
    _record_task(history, "t1", "headers ok")
    _record_task(history, "t2", "tls ok")
    _record_task(history, "t3", "cookies ok")
    reports = ReportManager(ReportRepository(tmp_path / "toolkit.db"), history)
    return history, reports


def test_report_lifecycle_and_render(tmp_path: Path) -> None:
    _history, reports = _setup(tmp_path)
    report = reports.create(
        "Web 安全报告",
        template="web_security",
        author="tester",
    )
    reports.add_task(report.report_id, "t1", "security_headers")
    reports.add_task(report.report_id, "t2", "tls")
    reports.add_task(report.report_id, "t3", "cookies")
    loaded = reports.get(report.report_id)
    assert loaded is not None
    assert [ref.task_id for ref in loaded.task_refs] == ["t1", "t2", "t3"]
    markdown = reports.render_markdown(report.report_id)
    assert markdown is not None
    assert "# Web 安全报告" in markdown
    assert "HIGH" in markdown
    assert "本报告包含 3 个分析任务" in markdown
    assert "缺少 Content-Security-Policy" in markdown


def test_report_export(tmp_path: Path) -> None:
    _history, reports = _setup(tmp_path)
    report = reports.create("导出测试", template="basic")
    reports.add_task(report.report_id, "t1", "findings")
    markdown_path = reports.export(report.report_id, tmp_path / "report.md")
    assert "# 导出测试" in markdown_path.read_text(encoding="utf-8")
    json_path = reports.export(report.report_id, tmp_path / "report.json")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["title"] == "导出测试"


def test_referenced_task_cannot_be_deleted(tmp_path: Path) -> None:
    history, reports = _setup(tmp_path)
    report = reports.create("引用报告", template="basic")
    reports.add_task(report.report_id, "t1", "findings")
    ok, message = history.delete("t1")
    assert not ok
    assert "报告引用" in message
    reports.remove_task(report.report_id, "t1")
    ok, _message = history.delete("t1")
    assert ok


def test_delete_report_keeps_tasks(tmp_path: Path) -> None:
    history, reports = _setup(tmp_path)
    report = reports.create("待删报告", template="basic")
    reports.add_task(report.report_id, "t1", "findings")
    reports.delete(report.report_id)
    assert reports.get(report.report_id) is None
    assert history.get("t1") is not None
