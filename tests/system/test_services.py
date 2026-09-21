"""Services tool: findings and status filtering with injected provider."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.system import ServiceInfo, WindowsServiceProvider
from modules.system.services import ServicesTool, _service_findings


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-svc",
        tool_id="system.services",
        logger=logging.getLogger("tests.svc"),
        cancel_event=threading.Event(),
    )


class FakeServiceProvider(WindowsServiceProvider):
    def __init__(self) -> None:
        self.services = [
            ServiceInfo(
                "svc1",
                "Service One",
                "RUNNING",
                "AUTO",
                "LocalSystem",
                "desc",
                r'"C:\Program Files\A\a.exe"',
            ),
            ServiceInfo(
                "svc2",
                "Service Two",
                "STOPPED",
                "DEMAND",
                "NT AUTHORITY\\NetworkService",
                "",
                r"C:\Program Files\B App\b.exe",
            ),
            ServiceInfo(
                "svc3", "Service Three", "RUNNING", "AUTO", "LocalSystem", "", r"C:\missing\svc.exe"
            ),
        ]
        self.errors: list[str] = []

    def list_services(self) -> tuple[list[ServiceInfo], list[str]]:
        return self.services, self.errors


def test_services_rows_and_filter() -> None:
    provider = FakeServiceProvider()
    result = ServicesTool(provider=provider).run({}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert len(result.data) == 3
    assert result.data[0]["start_type"] == "自动"
    running = ServicesTool(provider=provider).run({"status_filter": "RUNNING"}, _context())
    assert len(running.data) == 2


def test_service_findings() -> None:
    rows = [
        {"name": "svc2", "binary_path": r"C:\Program Files\B App\b.exe"},
        {"name": "svc3", "binary_path": r"C:\missing\svc.exe"},
        {"name": "svc1", "binary_path": '"C:\\Program Files\\A\\a.exe"'},
    ]
    findings = _service_findings(rows, "system.services")
    titles = {finding.title for finding in findings}
    assert "服务映像路径不存在" in titles
    assert "服务路径包含空格且未使用引号" in titles
