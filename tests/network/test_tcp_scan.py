"""TCP scan: port parsing, local integration, progress, concurrency and cancel."""

from __future__ import annotations

import logging
import socket
import threading
import time
from itertools import pairwise
from typing import Any

import pytest

from core.exceptions import TaskCancelledError, ToolInputError
from core.result import ResultStatus
from core.task import ExecutionContext, TaskStatus
from core.task_manager import TaskManager
from infrastructure.network import PortProbeResult, ProbeStatus
from modules.network.tcp_scan import TcpScanTool, parse_ports


def _context(on_progress: Any = None, event: threading.Event | None = None) -> ExecutionContext:
    return ExecutionContext(
        task_id="t-scan",
        tool_id="network.tcp_scan",
        logger=logging.getLogger("tests.scan"),
        cancel_event=event or threading.Event(),
        on_progress=on_progress,
    )


class FakeScanClient:
    def __init__(self, delay: float = 0.0, status: ProbeStatus = ProbeStatus.CLOSED) -> None:
        self.delay = delay
        self.status = status
        self.max_concurrent = 0
        self._active = 0
        self._lock = threading.Lock()

    def check_port(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        *,
        is_cancelled: Any = None,
    ) -> PortProbeResult:
        with self._lock:
            self._active += 1
            self.max_concurrent = max(self.max_concurrent, self._active)
        try:
            if self.delay:
                time.sleep(self.delay)
        finally:
            with self._lock:
                self._active -= 1
        return PortProbeResult(
            host=host,
            port=port,
            family="IPv4",
            resolved_address="127.0.0.1",
            status=self.status,
            latency_ms=0.1,
        )


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("80", [80]),
        (" 443 ", [443]),
        ("80-85", [80, 81, 82, 83, 84, 85]),
        ("1-3", [1, 2, 3]),
    ],
)
def test_parse_ports_valid(spec: str, expected: list[int]) -> None:
    assert parse_ports(spec) == expected


@pytest.mark.parametrize(
    "spec",
    ["", "abc", "80-443-90", "100-1", "0", "1-70000", "80-", "-80"],
)
def test_parse_ports_invalid(spec: str) -> None:
    with pytest.raises(ToolInputError):
        parse_ports(spec)


@pytest.fixture
def open_servers() -> list[int]:
    servers: list[socket.socket] = []
    threads: list[threading.Thread] = []
    ports: list[int] = []
    for _ in range(3):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        servers.append(server)
        ports.append(int(server.getsockname()[1]))

        def accept_once(sock: socket.socket = server) -> None:
            connection, _ = sock.accept()
            connection.close()

        thread = threading.Thread(target=accept_once, daemon=True)
        thread.start()
        threads.append(thread)
    yield sorted(ports)
    for server in servers:
        server.close()


def test_scan_local_range(open_servers: list[int]) -> None:
    first, last = open_servers[0], open_servers[-1]
    tool = TcpScanTool()
    result = tool.run(
        {"target": "127.0.0.1", "ports": f"{first}-{last}", "timeout": 3000, "concurrency": 16},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert len(result.data) == last - first + 1
    statuses = {int(row["port"]): row["status"] for row in result.data}
    for port in open_servers:
        assert statuses[port] == "OPEN"
    assert "service_hint" in result.data[0]
    assert "开放 3" in result.summary
    # ports are reported in ascending order
    assert [int(row["port"]) for row in result.data] == list(range(first, last + 1))


def test_scan_reports_progress() -> None:
    progress: list[float] = []
    messages: list[str] = []
    client = FakeScanClient(delay=0.002)
    tool = TcpScanTool(client=client)

    def on_progress(value: float, message: str | None) -> None:
        progress.append(value)
        if message:
            messages.append(message)

    result = tool.run(
        {"target": "127.0.0.1", "ports": "1-30", "timeout": 1000, "concurrency": 8},
        _context(on_progress=on_progress),
    )
    assert result.status is ResultStatus.SUCCESS
    assert progress and progress[-1] == 100.0
    assert all(later >= earlier for earlier, later in pairwise(progress))
    assert messages and "开放 0" in messages[-1]


def test_scan_concurrency_is_bounded() -> None:
    client = FakeScanClient(delay=0.005)
    tool = TcpScanTool(client=client)
    tool.run(
        {"target": "127.0.0.1", "ports": "1-80", "timeout": 1000, "concurrency": 4},
        _context(),
    )
    assert client.max_concurrent <= 4


def test_scan_cancellation_propagates() -> None:
    event = threading.Event()
    client = FakeScanClient(delay=0.01)
    tool = TcpScanTool(client=client)

    def on_progress(_value: float, _message: str | None) -> None:
        event.set()

    with pytest.raises(TaskCancelledError):
        tool.run(
            {"target": "127.0.0.1", "ports": "1-500", "timeout": 1000, "concurrency": 4},
            _context(on_progress=on_progress, event=event),
        )


def test_task_manager_cancels_scan() -> None:
    manager = TaskManager(max_workers=2)
    tool = TcpScanTool(client=FakeScanClient(delay=0.02))
    try:
        task_id = manager.submit_tool(
            tool,
            {"target": "127.0.0.1", "ports": "1-2000", "timeout": 1000, "concurrency": 4},
        )
        time.sleep(0.15)
        manager.cancel(task_id)
        snapshot = manager.wait(task_id, timeout=10.0)
        assert snapshot.status is TaskStatus.CANCELLED
    finally:
        manager.shutdown(wait=True)


def test_large_scan_adds_risk_finding() -> None:
    client = FakeScanClient()
    tool = TcpScanTool(client=client)
    result = tool.run(
        {"target": "127.0.0.1", "ports": "1-3000", "timeout": 1000, "concurrency": 32},
        _context(),
    )
    assert result.findings
    assert result.findings[0].title == "大范围端口扫描"
    assert result.findings[0].kind.value == "RISK"
