"""Process listing and detail tools with injected providers."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.system import ProcessDetail, ProcessInfo, ProcessProvider
from modules.system.process_detail import ProcessDetailTool
from modules.system.processes import ProcessesTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-proc",
        tool_id="system.processes",
        logger=logging.getLogger("tests.proc"),
        cancel_event=threading.Event(),
    )


def _process(pid: int, name: str, exe: str = "C:\\bin\\x.exe") -> ProcessInfo:
    return ProcessInfo(
        pid=pid,
        name=name,
        username="tester",
        cpu_percent=1.0,
        memory_percent=2.0,
        rss=1024,
        status="running",
        created="2026-09-20T00:00:00+00:00",
        exe=exe,
    )


class FakeProcessProvider(ProcessProvider):
    def __init__(self) -> None:
        self.processes = [
            _process(1, "python.exe", r"C:\Python\python.exe"),
            _process(2, "notepad.exe"),
            _process(3, "secret.exe", "[无法读取]"),
        ]
        self.denied = 2
        self.detail: ProcessDetail | None = None

    def list_processes(self) -> tuple[list[ProcessInfo], int]:
        return self.processes, self.denied

    def get_process_detail(self, pid: int) -> ProcessDetail | None:
        return self.detail


def test_process_list_and_filter() -> None:
    provider = FakeProcessProvider()
    result = ProcessesTool(provider=provider).run({}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert len(result.data) == 3
    assert result.data[2]["exe"] == "[无法读取]"
    assert any(finding.title == "部分进程信息无法读取" for finding in result.findings)
    filtered = ProcessesTool(provider=provider).run({"filter": "python"}, _context())
    assert len(filtered.data) == 1


def test_process_detail() -> None:
    provider = FakeProcessProvider()
    provider.detail = ProcessDetail(
        pid=1,
        name="python.exe",
        username="tester",
        status="running",
        created="2026-09-20T00:00:00+00:00",
        cpu_percent=1.0,
        memory_percent=2.0,
        rss=1024,
        num_threads=8,
        exe=r"C:\Python\python.exe",
        cmdline="python app.py --token=secret",
        cwd=r"C:\work",
        environment_count=42,
    )
    result = ProcessDetailTool(provider=provider).run({"pid": 1}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["num_threads"] == 8
    assert result.findings[0].title == "命令行可能包含敏感信息"


def test_process_detail_missing() -> None:
    result = ProcessDetailTool(provider=FakeProcessProvider()).run({"pid": 999}, _context())
    assert result.status is ResultStatus.FAILED
    assert "权限不足" in result.summary
