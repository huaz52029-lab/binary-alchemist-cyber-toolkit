"""Connections tool with injected provider."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.system import ConnectionInfo, ConnectionProvider
from modules.system.connections import ConnectionsTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-conn",
        tool_id="system.connections",
        logger=logging.getLogger("tests.conn"),
        cancel_event=threading.Event(),
    )


class FakeConnectionProvider(ConnectionProvider):
    def list_connections(self) -> list[ConnectionInfo]:
        return [
            ConnectionInfo("TCP", "127.0.0.1", 443, "", 0, "LISTEN", 100, "server.exe"),
            ConnectionInfo(
                "TCP", "192.168.1.5", 53000, "1.2.3.4", 443, "ESTABLISHED", 200, "python.exe"
            ),
            ConnectionInfo("TCP", "::", 8080, "::", 0, "LISTEN", None, "Unknown"),
            ConnectionInfo("UDP", "0.0.0.0", 53, "", 0, "NONE", 300, "dns.exe"),
        ]


def test_connections_rows_and_findings() -> None:
    provider = FakeConnectionProvider()
    result = ConnectionsTool(provider=provider).run({}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert len(result.data) == 4
    assert result.data[2]["pid"] == "-"
    assert result.data[2]["process_name"] == "Unknown"
    assert any(finding.title == "存在监听端口" for finding in result.findings)
    filtered = ConnectionsTool(provider=provider).run({"filter": "ESTABLISHED"}, _context())
    assert len(filtered.data) == 1
    by_port = ConnectionsTool(provider=provider).run({"filter": "443"}, _context())
    assert len(by_port.data) == 2
