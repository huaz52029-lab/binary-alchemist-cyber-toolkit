"""Database robustness: corruption quarantine, dangling refs and missing artifacts."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from core.history.history_repository import HistoryRepository
from core.history.task_history import TaskHistoryManager
from core.reports.report_manager import ReportManager
from core.reports.report_repository import ReportRepository
from core.result import ResultStatus, ToolResult
from core.task import Task, TaskStatus


def _task(task_id: str) -> Task:
    now = datetime.now(UTC)
    task = Task(task_id=task_id, tool_id="crypto.hash", params={})
    task.status = TaskStatus.COMPLETED
    task.started_at = now
    task.finished_at = now
    task.result = ToolResult(status=ResultStatus.SUCCESS, summary="ok")
    return task


def test_corrupt_database_is_quarantined_and_recreated(tmp_path: Path) -> None:
    db = tmp_path / "toolkit.db"
    db.write_bytes(b"this is definitely not a sqlite file")
    manager = TaskHistoryManager(db, tmp_path / "results")
    manager.record_task(_task("t-after-recovery"))
    assert manager.get("t-after-recovery") is not None
    manager.close()
    backups = list(tmp_path.glob("toolkit.db.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"this is definitely not a sqlite file"


def test_empty_database_file_opens_fresh(tmp_path: Path) -> None:
    db = tmp_path / "toolkit.db"
    db.write_bytes(b"")
    manager = TaskHistoryManager(db, tmp_path / "results")
    assert manager.repository.schema_version == 1
    manager.close()


def test_future_schema_version_is_left_alone(tmp_path: Path) -> None:
    db = tmp_path / "toolkit.db"
    repository = HistoryRepository(db)
    assert repository.schema_version == 1
    repository.close()
    # A database written by a newer build must not be migrated backwards.
    import sqlite3

    connection = sqlite3.connect(db)
    connection.execute("PRAGMA user_version = 99")
    connection.commit()
    connection.close()
    reopened = HistoryRepository(db)
    assert reopened.schema_version == 99
    reopened.close()


def test_missing_artifact_loads_none_gracefully(tmp_path: Path) -> None:
    manager = TaskHistoryManager(tmp_path / "toolkit.db", tmp_path / "results")
    now = datetime.now(UTC)
    task = Task(task_id="t-missing-artifact", tool_id="crypto.hash", params={})
    task.status = TaskStatus.COMPLETED
    task.started_at = now
    task.finished_at = now
    task.result = ToolResult(status=ResultStatus.SUCCESS, summary="ok")
    manager.record_task(task)
    import sqlite3

    connection = sqlite3.connect(tmp_path / "toolkit.db")
    connection.execute(
        "UPDATE tasks SET artifact_path = 'C:/nowhere/results/t-missing-artifact.json', "
        "result_json = NULL "
        "WHERE task_id = 't-missing-artifact'"
    )
    connection.commit()
    connection.close()
    assert manager.load_result("t-missing-artifact") is None
    manager.close()


def test_dangling_report_reference_is_rendered_explicitly(tmp_path: Path) -> None:
    history = TaskHistoryManager(tmp_path / "toolkit.db", tmp_path / "results")
    reports = ReportManager(ReportRepository(tmp_path / "toolkit.db"), history)
    report = reports.create("悬空引用报告", template="basic")
    reports.add_task(report.report_id, "t-does-not-exist", "findings")
    markdown = reports.render_markdown(report.report_id)
    assert markdown is not None
    assert "[缺失引用] t-does-not-exist" in markdown
    history.close()
    reports.close()


def test_delete_after_artifact_removed_by_user_is_safe(tmp_path: Path) -> None:
    manager = TaskHistoryManager(tmp_path / "toolkit.db", tmp_path / "results")
    task = _task("t-artifact-gone")
    task.result = ToolResult(
        status=ResultStatus.SUCCESS,
        summary="big",
        data=[{"text": "x" * (80 * 1024)}],
    )
    manager.record_task(task)
    artifact = Path(manager.get("t-artifact-gone")["artifact_path"])
    artifact.unlink()
    ok, _message = manager.delete("t-artifact-gone")
    assert ok
    assert manager.get("t-artifact-gone") is None
    manager.close()
