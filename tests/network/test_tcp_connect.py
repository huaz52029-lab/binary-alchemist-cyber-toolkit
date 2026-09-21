"""TCP connect: classification, socket probing and tool behavior."""

from __future__ import annotations

import logging
import socket
import threading
from typing import Any

import pytest

from core.exceptions import ToolInputError
from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.network import ProbeStatus, TcpClient, classify_socket_error
from modules.network.tcp_connect import TCPConnectTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-tcp",
        tool_id="network.tcp_connect",
        logger=logging.getLogger("tests.tcp"),
        cancel_event=threading.Event(),
    )


@pytest.fixture
def local_server() -> int:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = int(server.getsockname()[1])

    def accept_once() -> None:
        connection, _ = server.accept()
        connection.close()

    thread = threading.Thread(target=accept_once, daemon=True)
    thread.start()
    yield port
    server.close()


def _closed_port() -> int:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = int(probe.getsockname()[1])
    probe.close()
    return port


class _FakeSocket:
    def __init__(self, error: OSError | None = None) -> None:
        self.error = error
        self.timeout: float | None = None
        self.connected: tuple[Any, ...] | None = None

    def __enter__(self) -> _FakeSocket:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def settimeout(self, value: float) -> None:
        self.timeout = value

    def connect(self, address: tuple[Any, ...]) -> None:
        self.connected = address
        if self.error is not None:
            raise self.error


def test_classify_socket_error() -> None:
    assert classify_socket_error(TimeoutError("t")) == (ProbeStatus.TIMEOUT, "连接超时。")
    assert classify_socket_error(ConnectionRefusedError("r"))[0] is ProbeStatus.CLOSED
    assert classify_socket_error(socket.gaierror("d"))[0] is ProbeStatus.ERROR


def test_open_port(local_server: int) -> None:
    result = TcpClient().check_port("127.0.0.1", local_server, timeout=2.0)
    assert result.status is ProbeStatus.OPEN
    assert result.family == "IPv4"
    assert result.resolved_address == "127.0.0.1"
    assert result.latency_ms is not None


def test_closed_port() -> None:
    result = TcpClient().check_port("127.0.0.1", _closed_port(), timeout=5.0)
    assert result.status is ProbeStatus.CLOSED
    assert result.error is not None


def test_timeout_is_classified(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "infrastructure.network.socket_client.socket.getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 80))],
    )
    monkeypatch.setattr(
        "infrastructure.network.socket_client.socket.socket",
        lambda *args, **kwargs: _FakeSocket(error=TimeoutError("timeout")),
    )
    result = TcpClient().check_port("10.0.0.1", 80, timeout=0.5)
    assert result.status is ProbeStatus.TIMEOUT


def test_ipv6_address_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "infrastructure.network.socket_client.socket.getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("::1", 80, 0, 0))],
    )
    monkeypatch.setattr(
        "infrastructure.network.socket_client.socket.socket",
        lambda *args, **kwargs: _FakeSocket(),
    )
    result = TcpClient().check_port("::1", 80, timeout=1.0)
    assert result.status is ProbeStatus.OPEN
    assert result.family == "IPv6"


def test_invalid_port_raises() -> None:
    with pytest.raises(ToolInputError):
        TcpClient().check_port("127.0.0.1", 0)
    with pytest.raises(ToolInputError):
        TcpClient().check_port("127.0.0.1", 70000)


def test_tool_open_result(local_server: int) -> None:
    result = TCPConnectTool().run(
        {"target": "127.0.0.1", "port": local_server, "timeout": 2000},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["status"] == "OPEN"
    assert "开放" in result.summary
    assert result.findings[0].kind.value == "FACT"
    assert result.metadata["display"]["sections"]


def test_tool_invalid_params_fail_gracefully() -> None:
    result = TCPConnectTool().run({"target": "127.0.0.1", "port": 0}, _context())
    assert result.status is ResultStatus.FAILED
    assert "参数无效" in result.summary
