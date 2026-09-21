"""Low-level TCP connectivity probing built on the standard ``socket`` module."""

from __future__ import annotations

import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from core.exceptions import TaskCancelledError, ToolInputError


class ProbeStatus(StrEnum):
    """Outcome of a single TCP connection attempt."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class PortProbeResult:
    """Structured outcome of probing one host:port pair."""

    host: str
    port: int
    family: str
    resolved_address: str
    status: ProbeStatus
    latency_ms: float | None = None
    error: str | None = None


_UNREACHABLE_ERRNOS = {10051, 10065, 101, 113}  # ENETUNREACH / EHOSTUNREACH


def classify_socket_error(exc: OSError) -> tuple[ProbeStatus, str]:
    """Map an OSError to a probe status and a human-readable reason."""
    if isinstance(exc, TimeoutError):
        return ProbeStatus.TIMEOUT, "连接超时。"
    if isinstance(exc, ConnectionRefusedError):
        return ProbeStatus.CLOSED, "连接被拒绝（端口未开放或服务未监听）。"
    if isinstance(exc, socket.gaierror):
        return ProbeStatus.ERROR, "域名解析失败，请检查目标地址。"
    if getattr(exc, "errno", None) in _UNREACHABLE_ERRNOS:
        return ProbeStatus.ERROR, "目标网络不可达。"
    return ProbeStatus.ERROR, f"连接失败：{exc}"


class TcpClient:
    """Performs bounded TCP connection checks with IPv4/IPv6 support."""

    def __init__(self, *, default_timeout: float = 3.0, max_timeout: float = 10.0) -> None:
        if default_timeout <= 0 or max_timeout <= 0 or default_timeout > max_timeout:
            raise ValueError("invalid TCP timeout configuration")
        self._default_timeout = default_timeout
        self._max_timeout = max_timeout

    def check_port(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> PortProbeResult:
        """Probe one host:port and return a structured result.

        ``is_cancelled`` is checked between address attempts; when it returns
        true a :class:`TaskCancelledError` is raised so callers can abort early.
        """
        if not host.strip():
            raise ToolInputError("host must not be empty", user_message="目标地址不能为空。")
        if not 1 <= port <= 65535:
            raise ToolInputError(
                f"port out of range: {port}", user_message="端口必须在 1-65535 之间。"
            )
        effective_timeout = min(
            self._default_timeout if timeout is None else timeout, self._max_timeout
        )
        try:
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror:
            return PortProbeResult(
                host=host,
                port=port,
                family="IPv4",
                resolved_address="",
                status=ProbeStatus.ERROR,
                error="域名解析失败，请检查目标地址。",
            )
        last_status = ProbeStatus.ERROR
        last_error = "连接失败。"
        for family, socktype, proto, _canonname, sockaddr in infos:
            if is_cancelled is not None and is_cancelled():
                raise TaskCancelledError()
            address = str(sockaddr[0])
            started = time.perf_counter()
            try:
                with socket.socket(family, socktype, proto) as sock:
                    sock.settimeout(effective_timeout)
                    sock.connect(sockaddr)
                return PortProbeResult(
                    host=host,
                    port=port,
                    family="IPv6" if family is socket.AF_INET6 else "IPv4",
                    resolved_address=address,
                    status=ProbeStatus.OPEN,
                    latency_ms=(time.perf_counter() - started) * 1000.0,
                )
            except OSError as exc:
                last_status, last_error = classify_socket_error(exc)
        return PortProbeResult(
            host=host,
            port=port,
            family="IPv6" if infos[0][0] is socket.AF_INET6 else "IPv4",
            resolved_address=str(infos[0][4][0]),
            status=last_status,
            error=last_error,
        )
