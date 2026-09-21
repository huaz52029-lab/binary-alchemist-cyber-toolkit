from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from core.logger import LoggerManager
from core.result import ResultStatus
from core.task_manager import TaskManager
from ui.bridge import LogBridge, TaskBridge


def test_task_bridge_emits_lifecycle(qapp: QApplication) -> None:
    manager = TaskManager(max_workers=2)
    bridge = TaskBridge(manager)
    created_spy = QSignalSpy(bridge.task_created)
    finished_spy = QSignalSpy(bridge.task_finished)
    try:
        task_id = manager.submit(
            "test.tool",
            {},
            lambda context: context.make_result(ResultStatus.SUCCESS, "ok"),
        )
        manager.wait(task_id, timeout=5.0)
        if created_spy.count() == 0:
            assert created_spy.wait(2000)
        assert created_spy.count() >= 1
        if finished_spy.count() == 0:
            assert finished_spy.wait(2000)
        assert finished_spy.count() >= 1
    finally:
        bridge.detach()
        manager.shutdown(wait=True)


def test_log_bridge_forwards_records(qapp: QApplication, tmp_path: Path) -> None:
    logger_manager = LoggerManager(tmp_path / "logs", console=False)
    logger_manager.setup()
    bridge = LogBridge()
    logger_manager.attach_sink(bridge.handler)
    spy = QSignalSpy(bridge.message_emitted)
    try:
        logging.getLogger("tests.bridge").info("hello bridge")
        if spy.count() == 0:
            assert spy.wait(2000)
        assert spy.count() >= 1
        args = spy.at(spy.count() - 1)
        assert args[0] == "INFO"
        assert "hello bridge" in args[1]
    finally:
        logger_manager.shutdown()
