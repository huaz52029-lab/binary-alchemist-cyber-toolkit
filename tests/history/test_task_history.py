"""Task history persistence, pagination, filters, deletion and recovery."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.history.task_history import TaskHistoryManager
from core.result import ResultStatus, ToolResult
from core.task import Task, TaskStatus


def _task(task_id: str, tool_id: str, status: TaskStatus, summary: str) -> Task:
    now = datetime.now(UTC)
    task = Task(task_id=task_id, tool_id=tool_id, params={"input": "example"})
    task.status = status
    task.started_at = now - timedelta(seconds=1)
    task.finished_at = now
    task.result = ToolResult(
        status=ResultStatus.SUCCESS if status is TaskStatus.COMPLETED else ResultStatus.FAILED,
        summary=summary,
    )
    return task


def _manager(tmp_path: Path) -> TaskHistoryManager:
    return TaskHistoryManager(
        tmp_path / "toolkit.db",
        tmp_path / "results",
    )


def test_save_and_query(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    manager.record_task(_task("t1", "network.ping", TaskStatus.COMPLETED, "ping ok"))
    manager.record_task(_task("t2", "crypto.hash", TaskStatus.FAILED, "hash failed"))
    rows, total = manager.query()
    assert total == 2
    assert rows[0]["task_id"] == "t2"  # newest first
    filtered, total = manager.query(status="COMPLETED")
    assert total == 1
    assert filtered[0]["task_id"] == "t1"
    _searched, total = manager.query(search="ping")
    assert total == 1


def test_pagination(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    for index in range(120):
        manager.record_task(
            _task(
                f"t{index:04d}",
                "crypto.hash",
                TaskStatus.COMPLETED,
                f"summary {index}",
            )
        )
    rows, total = manager.query(limit=50, offset=0)
    assert total == 120
    assert len(rows) == 50
    rows2, _total = manager.query(limit=50, offset=100)
    assert len(rows2) == 20


def test_result_artifact_and_cleanup(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    task = _task("t-big", "file_analysis.strings", TaskStatus.COMPLETED, "big")
    task.result = ToolResult(
        status=ResultStatus.SUCCESS,
        summary="big",
        data=[{"text": "x" * (80 * 1024)}],
    )
    manager.record_task(task)
    record = manager.get("t-big")
    assert record["artifact_path"]
    assert Path(record["artifact_path"]).is_file()
    loaded = manager.load_result("t-big")
    assert loaded is not None
    assert len(loaded.data[0]["text"]) == 80 * 1024
    ok, _message = manager.delete("t-big")
    assert ok
    assert not Path(record["artifact_path"]).exists()


def test_safe_params_persisted_only_when_declared(tmp_path: Path) -> None:
    from core.tool_registry import ToolRegistry

    registry = ToolRegistry()
    from modules import register_builtin_tools

    register_builtin_tools(registry)
    manager = TaskHistoryManager(
        tmp_path / "toolkit.db",
        tmp_path / "results",
        registry,
    )
    safe = _task("t-safe", "encoding.base64", TaskStatus.COMPLETED, "ok")
    manager.record_task(safe)
    assert manager.get("t-safe")["params_json"] is not None
    sensitive = _task("t-secret", "crypto.jwt", TaskStatus.COMPLETED, "ok")
    manager.record_task(sensitive)
    assert manager.get("t-secret")["params_json"] is None


def test_interrupted_tasks_recovered(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    manager.record_task(_task("t-run", "crypto.hash", TaskStatus.RUNNING, "running"))
    manager.close()
    reopened = _manager(tmp_path)
    record = reopened.get("t-run")
    assert record["status"] == "FAILED"
    assert "中断" in (record.get("error_message") or "")


def test_clear_history(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    manager.record_task(_task("t1", "crypto.hash", TaskStatus.COMPLETED, "ok"))
    count, message = manager.clear()
    assert count == 0  # no artifacts
    assert message == "历史已清空。"
    _rows, total = manager.query()
    assert total == 0
