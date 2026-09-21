from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from core.exceptions import TaskCancelledError, ToolInputError
from core.result import ResultStatus
from core.task import ExecutionContext, TaskStatus
from core.task_manager import TaskManager
from tests.conftest import DummyTool


def _ok(context: ExecutionContext) -> Any:
    return context.make_result(ResultStatus.SUCCESS, "ok", data=[{"x": 1}])


def test_submit_and_wait_success() -> None:
    manager = TaskManager(max_workers=2)
    try:
        task_id = manager.submit("test.tool", {"x": 1}, _ok)
        snapshot = manager.wait(task_id, timeout=5.0)
        assert snapshot.status is TaskStatus.COMPLETED
        assert snapshot.result is not None
        assert snapshot.result.status is ResultStatus.SUCCESS
        assert snapshot.params == {"x": 1}
    finally:
        manager.shutdown(wait=True)


def test_exception_becomes_failed() -> None:
    manager = TaskManager(max_workers=2)

    def boom(context: ExecutionContext) -> Any:
        raise ValueError("boom")

    try:
        task_id = manager.submit("test.tool", {}, boom)
        snapshot = manager.wait(task_id, timeout=5.0)
        assert snapshot.status is TaskStatus.FAILED
        assert snapshot.result is not None
        assert snapshot.result.status is ResultStatus.FAILED
        assert "未知错误" in snapshot.result.summary
    finally:
        manager.shutdown(wait=True)


def test_cancel_running_task() -> None:
    manager = TaskManager(max_workers=2)
    started = threading.Event()

    def loop(context: ExecutionContext) -> Any:
        started.set()
        while True:
            context.raise_if_cancelled()
            time.sleep(0.01)

    try:
        task_id = manager.submit("test.tool", {}, loop)
        assert started.wait(timeout=2.0)
        time.sleep(0.05)
        assert manager.cancel(task_id)
        snapshot = manager.wait(task_id, timeout=5.0)
        assert snapshot.status is TaskStatus.CANCELLED
    finally:
        manager.shutdown(wait=True)


def test_wait_timeout_marks_task() -> None:
    manager = TaskManager(max_workers=2)

    def slow(context: ExecutionContext) -> Any:
        time.sleep(0.5)
        return context.make_result(ResultStatus.SUCCESS, "late")

    try:
        task_id = manager.submit("test.tool", {}, slow)
        snapshot = manager.wait(task_id, timeout=0.05)
        assert snapshot.status is TaskStatus.TIMEOUT
    finally:
        manager.shutdown(wait=True)


def test_max_workers_are_respected() -> None:
    manager = TaskManager(max_workers=2)
    entered = 0
    lock = threading.Lock()
    release = threading.Event()

    def block(context: ExecutionContext) -> Any:
        nonlocal entered
        with lock:
            entered += 1
        release.wait(timeout=5.0)
        return context.make_result(ResultStatus.SUCCESS, "done")

    try:
        task_ids = [manager.submit("test.tool", {}, block) for _ in range(3)]
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            with lock:
                if entered >= 2:
                    break
            time.sleep(0.01)
        time.sleep(0.05)
        with lock:
            assert entered == 2
        release.set()
        snapshots = [manager.wait(task_id, timeout=5.0) for task_id in task_ids]
        assert all(snapshot.status is TaskStatus.COMPLETED for snapshot in snapshots)
    finally:
        manager.shutdown(wait=True)


def test_progress_is_recorded() -> None:
    manager = TaskManager(max_workers=2)

    def work(context: ExecutionContext) -> Any:
        context.set_progress(75.0, "scanning")
        return context.make_result(ResultStatus.SUCCESS, "done")

    try:
        task_id = manager.submit("test.tool", {}, work)
        snapshot = manager.wait(task_id, timeout=5.0)
        assert snapshot.progress == 75.0
    finally:
        manager.shutdown(wait=True)


def test_listeners_receive_state_changes() -> None:
    manager = TaskManager(max_workers=2)
    seen: list[TaskStatus] = []
    manager.subscribe(lambda task: seen.append(task.status))
    try:
        task_id = manager.submit("test.tool", {}, _ok)
        manager.wait(task_id, timeout=5.0)
        assert TaskStatus.COMPLETED in seen
    finally:
        manager.shutdown(wait=True)


def test_pending_is_notified_before_running() -> None:
    manager = TaskManager(max_workers=2)
    seen: list[TaskStatus] = []
    manager.subscribe(lambda task: seen.append(task.status))
    release = threading.Event()

    def block(context: ExecutionContext) -> Any:
        release.wait(timeout=2.0)
        return context.make_result(ResultStatus.SUCCESS, "done")

    try:
        task_id = manager.submit("test.tool", {}, block)
        assert seen[0] is TaskStatus.PENDING
        release.set()
        manager.wait(task_id, timeout=5.0)
        assert TaskStatus.RUNNING in seen
    finally:
        manager.shutdown(wait=True)


def test_submit_tool_records_tool_id(dummy_tool: DummyTool) -> None:
    manager = TaskManager(max_workers=2)
    try:
        task_id = manager.submit_tool(dummy_tool, {"value": "abc"})
        snapshot = manager.wait(task_id, timeout=5.0)
        assert snapshot.tool_id == "system.dummy"
        assert snapshot.result is not None
        assert "abc" in snapshot.result.summary
    finally:
        manager.shutdown(wait=True)


def test_unknown_task_raises() -> None:
    manager = TaskManager(max_workers=2)
    try:
        with pytest.raises(ToolInputError):
            manager.wait("nope", timeout=1.0)
    finally:
        manager.shutdown(wait=True)


def test_cancel_all() -> None:
    manager = TaskManager(max_workers=4)
    release = threading.Event()

    def block(context: ExecutionContext) -> Any:
        while not context.is_cancelled:
            if release.wait(timeout=0.05):
                break
        context.raise_if_cancelled()
        return context.make_result(ResultStatus.SUCCESS, "done")

    try:
        task_ids = [manager.submit("test.tool", {}, block) for _ in range(2)]
        time.sleep(0.1)
        assert manager.cancel_all() == 2
        for task_id in task_ids:
            assert manager.wait(task_id, timeout=5.0).status is TaskStatus.CANCELLED
    finally:
        release.set()
        manager.shutdown(wait=True)


def test_shutdown_rejects_new_submissions() -> None:
    manager = TaskManager(max_workers=2)
    manager.shutdown()
    with pytest.raises(ToolInputError):
        manager.submit("test.tool", {}, _ok)


def test_tool_input_error_keeps_human_message() -> None:
    manager = TaskManager(max_workers=2)

    def bad_input(context: ExecutionContext) -> Any:
        raise TaskCancelledError()

    try:
        task_id = manager.submit("test.tool", {}, bad_input)
        snapshot = manager.wait(task_id, timeout=5.0)
        assert snapshot.status is TaskStatus.CANCELLED
    finally:
        manager.shutdown(wait=True)
