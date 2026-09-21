"""TaskManager lifecycle races: cancel timing, status ordering and bursts."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext, Task, TaskStatus
from core.task_manager import TaskManager


def _blocking(label: str, gate: threading.Event) -> Callable[[ExecutionContext], ToolResult]:
    def body(context: ExecutionContext) -> ToolResult:
        context.info(f"{label} waiting")
        deadline = time.monotonic() + 10
        while not gate.is_set():
            context.raise_if_cancelled()
            if time.monotonic() > deadline:
                break
            time.sleep(0.01)
        context.raise_if_cancelled()
        return context.make_result(ResultStatus.SUCCESS, f"{label} done")

    return body


def test_pending_is_notified_before_running() -> None:
    """Regression: PENDING could be skipped when a worker raced ahead."""
    manager = TaskManager(max_workers=2)
    gate = threading.Event()
    statuses: list[TaskStatus] = []

    def listener(task: Task) -> None:
        statuses.append(task.status)

    manager.subscribe(listener)
    task_id = manager.submit("network.tcp_connect", {}, _blocking("t", gate))
    assert statuses[0] is TaskStatus.PENDING
    gate.set()
    snapshot = manager.wait(task_id, timeout=10)
    manager.shutdown(wait=True)
    assert statuses[0] is TaskStatus.PENDING
    assert TaskStatus.RUNNING in statuses
    assert snapshot.status is TaskStatus.COMPLETED


def test_cancel_immediately_after_submit_ends_cancelled() -> None:
    manager = TaskManager(max_workers=2)
    gate = threading.Event()
    task_id = manager.submit("network.tcp_connect", {}, _blocking("t", gate))
    assert manager.cancel(task_id) is True
    snapshot = manager.wait(task_id, timeout=10)
    gate.set()
    manager.shutdown(wait=True)
    assert snapshot.status is TaskStatus.CANCELLED
    assert snapshot.result is not None
    assert snapshot.result.status is ResultStatus.CANCELLED


def test_cancel_after_completion_returns_false() -> None:
    manager = TaskManager(max_workers=2)
    gate = threading.Event()
    gate.set()
    task_id = manager.submit("network.tcp_connect", {}, _blocking("t", gate))
    snapshot = manager.wait(task_id, timeout=10)
    assert snapshot.status is TaskStatus.COMPLETED
    assert manager.cancel(task_id) is False
    manager.shutdown(wait=True)
    assert manager.snapshot(task_id) is not None
    assert manager.snapshot(task_id).status is TaskStatus.COMPLETED


def test_cancel_after_failure_returns_false() -> None:
    manager = TaskManager(max_workers=2)

    def failing(context: ExecutionContext) -> ToolResult:
        raise ValueError("boom")

    task_id = manager.submit("network.tcp_connect", {}, failing)
    snapshot = manager.wait(task_id, timeout=10)
    assert snapshot.status is TaskStatus.FAILED
    assert manager.cancel(task_id) is False
    manager.shutdown(wait=True)
    assert manager.snapshot(task_id).status is TaskStatus.FAILED


def test_many_simultaneous_completions() -> None:
    manager = TaskManager(max_workers=8)
    gate = threading.Event()
    ids = [manager.submit("crypto.hash", {}, _blocking(f"t{i}", gate)) for i in range(64)]
    gate.set()
    snapshots = [manager.wait(task_id, timeout=20) for task_id in ids]
    manager.shutdown(wait=True)
    assert len(set(ids)) == 64
    assert all(snapshot.status is TaskStatus.COMPLETED for snapshot in snapshots)
    assert all(snapshot.result is not None for snapshot in snapshots)


def test_cancel_all_counts_and_finishes() -> None:
    manager = TaskManager(max_workers=4)
    gate = threading.Event()
    ids = [manager.submit("crypto.hash", {}, _blocking(f"t{i}", gate)) for i in range(12)]
    # Give the pool a moment to start a few workers, then cancel everything.
    time.sleep(0.05)
    cancelled = manager.cancel_all()
    snapshots = [manager.wait(task_id, timeout=20) for task_id in ids]
    gate.set()
    manager.shutdown(wait=True)
    assert cancelled == 12
    assert all(snapshot.status is TaskStatus.CANCELLED for snapshot in snapshots)
