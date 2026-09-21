"""System ICMP ping provider.

On Windows the stable ``IcmpSendEcho`` API (icmp.dll) is used, which is language
independent and needs no privileges. Other platforms fall back to the system
``ping`` command on a best-effort basis. Tools depend on this provider, never on
``subprocess`` or ctypes directly.
"""

from __future__ import annotations

import ctypes
import ipaddress
import logging
import platform
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from core.exceptions import TaskCancelledError, ToolInputError


class PingReplyStatus(StrEnum):
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class PingReply:
    sequence: int
    status: PingReplyStatus
    latency_ms: float | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PingStats:
    target: str
    resolved_address: str
    sent: int
    received: int
    lost: int
    loss_percent: float
    min_latency_ms: float | None
    max_latency_ms: float | None
    avg_latency_ms: float | None
    replies: tuple[PingReply, ...]


class PingProvider(Protocol):
    """Interface implemented by concrete ping backends."""

    def ping(
        self,
        target: str,
        count: int,
        timeout_ms: int,
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> PingStats: ...


def build_stats(target: str, resolved_address: str, replies: list[PingReply]) -> PingStats:
    """Aggregate per-reply outcomes into summary statistics."""
    sent = len(replies)
    latencies = [reply.latency_ms for reply in replies if reply.latency_ms is not None]
    received = len(latencies)
    lost = sent - received
    return PingStats(
        target=target,
        resolved_address=resolved_address,
        sent=sent,
        received=received,
        lost=lost,
        loss_percent=lost / sent * 100.0 if sent else 0.0,
        min_latency_ms=min(latencies) if latencies else None,
        max_latency_ms=max(latencies) if latencies else None,
        avg_latency_ms=sum(latencies) / len(latencies) if latencies else None,
        replies=tuple(replies),
    )


_ICMP_ERRORS = {
    11002: "目标不可达",
    11003: "目标主机不可达",
    11004: "目标协议不可达",
    11005: "目标端口不可达",
    11010: "请求超时",
    11013: "TTL 超时",
}


class _IpOptionInformation(ctypes.Structure):
    _fields_ = [
        ("ttl", ctypes.c_ubyte),
        ("tos", ctypes.c_ubyte),
        ("flags", ctypes.c_ubyte),
        ("options_size", ctypes.c_ubyte),
        ("options_data", ctypes.c_void_p),
    ]


class _IcmpEchoReply(ctypes.Structure):
    _fields_ = [
        ("address", ctypes.c_ulong),
        ("status", ctypes.c_ulong),
        ("round_trip_time", ctypes.c_ulong),
        ("data_size", ctypes.c_ushort),
        ("reserved", ctypes.c_ushort),
        ("data", ctypes.c_void_p),
        ("options", _IpOptionInformation),
    ]


class WindowsPingProvider:
    """ICMP echo provider using the Windows icmp.dll API."""

    def __init__(self, *, max_count: int = 10, max_timeout_ms: int = 5000) -> None:
        self._max_count = max_count
        self._max_timeout_ms = max_timeout_ms
        self._logger = logging.getLogger("infra.network.ping")

    def ping(
        self,
        target: str,
        count: int,
        timeout_ms: int,
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> PingStats:
        value = target.strip()
        if not value:
            raise ToolInputError("empty target", user_message="请输入目标地址。")
        if not 1 <= count <= self._max_count:
            raise ToolInputError(
                f"count out of range: {count}",
                user_message=f"Ping 次数必须在 1-{self._max_count} 之间。",
            )
        timeout_ms = min(max(1, timeout_ms), self._max_timeout_ms)
        try:
            address = ipaddress.ip_address(value)
        except ValueError as exc:
            raise ToolInputError(
                f"invalid IP target: {value}",
                user_message="Ping 目标必须是 IP 地址（当前版本不支持域名与 IPv6）。",
            ) from exc
        if address.version == 6:
            raise ToolInputError(
                "IPv6 target",
                user_message="当前版本 Ping 仅支持 IPv4 目标，IPv6 将在后续版本提供。",
            )
        if platform.system() == "Windows":
            replies = self._ping_windows(value, count, timeout_ms, is_cancelled)
        else:  # pragma: no cover - portable fallback
            replies = self._ping_subprocess(value, count, timeout_ms)
        return build_stats(value, value, replies)

    def _ping_windows(
        self,
        target: str,
        count: int,
        timeout_ms: int,
        is_cancelled: Callable[[], bool] | None,
    ) -> list[PingReply]:
        icmp = ctypes.WinDLL("icmp.dll", use_last_error=True)
        icmp.IcmpCreateFile.restype = ctypes.c_void_p
        icmp.IcmpSendEcho.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_void_p,
            ctypes.c_ushort,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        icmp.IcmpSendEcho.restype = ctypes.c_ulong
        icmp.IcmpCloseHandle.argtypes = [ctypes.c_void_p]
        handle = icmp.IcmpCreateFile()
        invalid_handle = ctypes.c_void_p(-1).value
        if not handle or handle == invalid_handle:
            raise OSError("IcmpCreateFile failed")
        packed = ipaddress.IPv4Address(target).packed
        ip_addr = ctypes.c_ulong(int.from_bytes(packed, "little"))
        payload = b"binary-alchemist"
        replies: list[PingReply] = []
        try:
            for sequence in range(1, count + 1):
                if is_cancelled is not None and is_cancelled():
                    raise TaskCancelledError()
                reply_size = ctypes.sizeof(_IcmpEchoReply) + len(payload)
                reply_buffer = ctypes.create_string_buffer(reply_size)
                sent = icmp.IcmpSendEcho(
                    handle,
                    ip_addr,
                    ctypes.c_char_p(payload),
                    len(payload),
                    None,
                    reply_buffer,
                    reply_size,
                    timeout_ms,
                )
                if sent == 0:
                    replies.append(
                        PingReply(
                            sequence=sequence, status=PingReplyStatus.ERROR, error="发送失败。"
                        )
                    )
                    continue
                echo = _IcmpEchoReply.from_buffer_copy(reply_buffer)
                if echo.status == 0:
                    replies.append(
                        PingReply(
                            sequence=sequence,
                            status=PingReplyStatus.SUCCESS,
                            latency_ms=float(echo.round_trip_time),
                        )
                    )
                else:
                    error = _ICMP_ERRORS.get(int(echo.status), f"ICMP 状态 {echo.status}")
                    status = (
                        PingReplyStatus.TIMEOUT
                        if int(echo.status) == 11010
                        else PingReplyStatus.ERROR
                    )
                    replies.append(PingReply(sequence=sequence, status=status, error=error))
        finally:
            icmp.IcmpCloseHandle(handle)
        return replies

    def _ping_subprocess(self, target: str, count: int, timeout_ms: int) -> list[PingReply]:
        command = [
            "ping",
            "-c",
            str(count),
            "-W",
            str(max(1, timeout_ms // 1000)),
            target,
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=count * (timeout_ms / 1000.0) + 2.0,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return [
                PingReply(sequence=index, status=PingReplyStatus.TIMEOUT, error="请求超时。")
                for index in range(1, count + 1)
            ]
        output = completed.stdout or ""
        times = [float(match) for match in re.findall(r"time[=<]([0-9.]+) ?ms", output)]
        replies: list[PingReply] = []
        for index in range(1, count + 1):
            if index <= len(times):
                replies.append(
                    PingReply(
                        sequence=index, status=PingReplyStatus.SUCCESS, latency_ms=times[index - 1]
                    )
                )
            else:
                replies.append(
                    PingReply(sequence=index, status=PingReplyStatus.ERROR, error="无响应。")
                )
        return replies
