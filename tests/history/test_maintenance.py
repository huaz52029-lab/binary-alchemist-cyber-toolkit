"""Database maintenance: orphan artifacts and broken report references."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from core.exceptions import FileSystemError
from core.history.artifacts import ArtifactManager
from core.history.maintenance import DatabaseMaintenance
from core.history.task_history import TaskHistoryManager
from core.reports.report_manager import ReportManager
from core.reports.report_repository import ReportRepository
from core.result import ResultStatus, ToolResult
from core.task import Task, TaskStatus


def _task(task_id: str, *, big: bool = False) -> Task:
    now = datetime.now(UTC)
    task = Task(task_id=task_id, tool_id="crypto.hash", params={})
    task.status = TaskStatus.COMPLETED
    task.started_at = now
    task.finished_at = now
    task.result = ToolResult(
        status=ResultStatus.SUCCESS,
        summary="ok",
        data=[{"text": "x" * (80 * 1024)}] if big else [],
    )
    return task


def _setup(tmp_path: Path) -> tuple[TaskHistoryManager, ReportManager, DatabaseMaintenance]:
    history = TaskHistoryManager(tmp_path / "toolkit.db", tmp_path / "results")
    reports = ReportManager(ReportRepository(tmp_path / "toolkit.db"), history)
    maintenance = DatabaseMaintenance(history, reports, tmp_path / "results")
    return history, reports, maintenance


def test_orphan_artifacts_are_reported_and_cleaned_on_request(tmp_path: Path) -> None:
    history, reports, maintenance = _setup(tmp_path)
    history.record_task(_task("t-kept", big=True))
    # A stray file with no matching task row.
    (tmp_path / "results" / "t-gone.json").write_text("{}", encoding="utf-8")
    orphans = maintenance.orphan_artifact_files()
    assert [path.stem for path in orphans] == ["t-gone"]
    assert maintenance.calculate_artifact_size() > 0
    removed = maintenance.cleanup_orphan_artifacts()
    assert removed == 1
    assert maintenance.orphan_artifact_files() == []
    assert (tmp_path / "results" / "t-kept.json").is_file()
    history.close()
    reports.close()


def test_broken_report_refs_are_reported_and_removed_on_request(tmp_path: Path) -> None:
    history, reports, maintenance = _setup(tmp_path)
    history.record_task(_task("t-real"))
    report = reports.create("维护测试", template="basic")
    reports.add_task(report.report_id, "t-real", "findings")
    reports.add_task(report.report_id, "t-missing", "findings")
    broken = maintenance.broken_report_refs()
    assert len(broken) == 1
    assert broken[0]["task_id"] == "t-missing"
    assert maintenance.remove_broken_refs() == 1
    assert maintenance.broken_report_refs() == []
    loaded = reports.get(report.report_id)
    assert loaded is not None
    assert [ref.task_id for ref in loaded.task_refs] == ["t-real"]
    history.close()
    reports.close()


def test_artifact_manager_rejects_path_escape(tmp_path: Path) -> None:
    manager = ArtifactManager(tmp_path / "results")
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    with pytest.raises(FileSystemError):
        manager.delete_artifact(outside)
    with pytest.raises(FileSystemError):
        manager.validate_path(tmp_path / ".." / "outside.json")
    assert outside.is_file()
