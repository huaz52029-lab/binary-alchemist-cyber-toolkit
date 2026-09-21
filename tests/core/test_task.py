from __future__ import annotations

import logging
import threading

import pytest
from pydantic import ValidationError

from core.exceptions import TaskCancelledError
from core.result import ResultStatus
from core.task import ExecutionContext, Task, TaskStatus
from core.task_result import TaskResult


def test_task_defaults() -> None:
    task = Task(tool_id="network.ping")
    assert task.status is TaskStatus.PENDING
    assert task.progress == 0.0
    assert task.created_at is not None
    assert task.result is None


def test_task_progress_validated_on_assignment() -> None:
    task = Task(tool_id="network.ping")
    with pytest.raises(ValidationError):
        task.progress = 150.0


def test_task_result_snapshot() -> None:
    task = Task(tool_id="network.ping", params={"host": "127.0.0.1"})
    snapshot = TaskResult.from_task(task)
    assert snapshot.task_id == task.task_id
    assert snapshot.tool_id == "network.ping"
    assert snapshot.params == {"host": "127.0.0.1"}


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-1",
        tool_id="network.ping",
        logger=logging.getLogger("tests.ctx"),
        cancel_event=threading.Event(),
    )


def test_execution_context_collects_logs() -> None:
    context = _context()
    context.info("hello")
    assert context.log_entries[-1].message == "hello"


def test_execution_context_cancellation() -> None:
    event = threading.Event()
    context = ExecutionContext(
        task_id="t-1",
        tool_id="network.ping",
        logger=logging.getLogger("tests.ctx"),
        cancel_event=event,
    )
    assert not context.is_cancelled
    event.set()
    assert context.is_cancelled
    with pytest.raises(TaskCancelledError):
        context.raise_if_cancelled()


def test_execution_context_make_result() -> None:
    context = _context()
    context.info("logged")
    result = context.make_result(ResultStatus.SUCCESS, "done")
    assert result.status is ResultStatus.SUCCESS
    assert result.logs == context.log_entries
    assert result.duration is not None and result.duration >= 0.0
