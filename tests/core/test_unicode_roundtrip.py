"""Unicode end-to-end: history, SQLite, exporters and reports stay intact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from core.exporters import ExportManager
from core.history.task_history import TaskHistoryManager
from core.reports.report_manager import ReportManager
from core.reports.report_repository import ReportRepository
from core.result import ResultStatus, ToolResult
from core.task import Task, TaskStatus


def test_unicode_survives_full_pipeline(tmp_path: Path) -> None:
    history = TaskHistoryManager(tmp_path / "toolkit.db", tmp_path / "results")
    reports = ReportManager(ReportRepository(tmp_path / "toolkit.db"), history)
    now = datetime.now(UTC)
    task = Task(task_id="t-unicode", tool_id="encoding.base64", params={})
    task.status = TaskStatus.COMPLETED
    task.started_at = now
    task.finished_at = now
    task.result = ToolResult(
        status=ResultStatus.SUCCESS,
        summary="你好 🔐 CTF测试",
        data=[{"value": "中文 Emoji 🚀 特殊：ß·—"}],
    )
    history.record_task(task)
    loaded = history.load_result("t-unicode")
    assert loaded is not None
    assert loaded.summary == "你好 🔐 CTF测试"
    assert loaded.data[0]["value"] == "中文 Emoji 🚀 特殊：ß·—"

    report = reports.create("中文报告 🔐", template="basic")
    reports.add_task(report.report_id, "t-unicode", "findings")
    markdown = reports.render_markdown(report.report_id)
    assert markdown is not None
    assert "你好 🔐 CTF测试" in markdown
    export_path = reports.export(report.report_id, tmp_path / "报告.md")
    assert "中文报告 🔐" in export_path.read_text(encoding="utf-8")

    exporters = ExportManager.with_defaults()
    assert "你好 🔐 CTF测试" in exporters.to_string(loaded, "txt")
    payload = json.loads(exporters.to_string(loaded, "json"))
    assert payload["summary"] == "你好 🔐 CTF测试"
    csv_text = exporters.to_string(loaded, "csv")
    assert "中文 Emoji 🚀" in csv_text
    history.close()
    reports.close()
