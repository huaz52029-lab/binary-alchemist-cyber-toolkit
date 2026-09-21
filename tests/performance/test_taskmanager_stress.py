"""TaskManager stress: high-volume submission, uniqueness and cancellation."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

import pytest

from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext, TaskStatus
from core.task_manager import TaskManager


def _fast(ok: bool = True) -> Callable[[ExecutionContext], ToolResult]:
    def body(context: ExecutionContext) -> ToolResult:
        if not ok:
            raise ValueError("deliberate failure")
        return context.make_result(ResultStatus.SUCCESS, "ok")

    return body


def _blocking(gate: threading.Event) -> Callable[[ExecutionContext], ToolResult]:
    def body(context: ExecutionContext) -> ToolResult:
        deadline = time.monotonic() + 20
        while not gate.is_set():
            context.raise_if_cancelled()
            if time.monotonic() > deadline:
                break
            time.sleep(0.005)
        context.raise_if_cancelled()
        return context.make_result(ResultStatus.SUCCESS, "ok")

    return body


@pytest.mark.parametrize("count", [100, 500, 1000])
def test_no_tasks_lost_under_load(count: int) -> None:
    manager = TaskManager(max_workers=16, default_timeout=60)
    ids = [manager.submit("crypto.hash", {"i": index}, _fast()) for index in range(count)]
    snapshots = [manager.wait(task_id, timeout=60) for task_id in ids]
    manager.shutdown(wait=True)
    assert len(ids) == count
    assert len(set(ids)) == count, "task ids must be unique"
    assert all(snapshot.status is TaskStatus.COMPLETED for snapshot in snapshots)
    assert manager.total_count() == count


def test_mixed_outcomes_account_for_every_task() -> None:
    manager = TaskManager(max_workers=8, default_timeout=60)
    ids = [
        manager.submit("crypto.hash", {"i": index}, _fast(ok=index % 5 != 0)) for index in range(50)
    ]
    snapshots = [manager.wait(task_id, timeout=60) for task_id in ids]
    manager.shutdown(wait=True)
    completed = sum(s.status is TaskStatus.COMPLETED for s in snapshots)
    failed = sum(s.status is TaskStatus.FAILED for s in snapshots)
    assert completed == 40
    assert failed == 10


def test_cancel_batch_midflight() -> None:
    manager = TaskManager(max_workers=4, default_timeout=60)
    gate = threading.Event()
    ids = [manager.submit("crypto.hash", {"i": index}, _blocking(gate)) for index in range(40)]
    time.sleep(0.05)
    targets = set(ids[::3])
    for task_id in targets:
        assert manager.cancel(task_id) is True
    gate.set()
    snapshots = {task_id: manager.wait(task_id, timeout=60) for task_id in ids}
    manager.shutdown(wait=True)
    cancelled = {
        task_id
        for task_id, snapshot in snapshots.items()
        if snapshot.status is TaskStatus.CANCELLED
    }
    assert cancelled == targets
    assert all(
        snapshot.status is TaskStatus.COMPLETED
        for task_id, snapshot in snapshots.items()
        if task_id not in targets
    )


def test_no_thread_leak_across_100_task_cycles() -> None:
    baseline = threading.active_count()
    manager = TaskManager(max_workers=4, default_timeout=60)
    peak = baseline
    for cycle in range(100):
        task_id = manager.submit("crypto.hash", {}, _fast())
        manager.wait(task_id, timeout=60)
        if cycle % 3 == 0:
            manager.cancel(task_id)  # cancel on a terminal task is a no-op
        peak = max(peak, threading.active_count())
    manager.shutdown(wait=True)
    assert peak <= baseline + 8, "worker threads must stay bounded across cycles"
