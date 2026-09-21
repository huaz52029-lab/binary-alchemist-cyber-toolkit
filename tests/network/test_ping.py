"""Ping tool: aggregation, validation, provider contract and tool behavior."""

from __future__ import annotations

import logging
import platform
import threading

import pytest

from core.exceptions import TaskCancelledError, ToolInputError
from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.network import (
    PingReply,
    PingReplyStatus,
    PingStats,
    WindowsPingProvider,
    build_stats,
)
from modules.network.ping import PingTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-ping",
        tool_id="network.ping",
        logger=logging.getLogger("tests.ping"),
        cancel_event=threading.Event(),
    )


def _stats(target: str, latencies: list[float | None]) -> PingStats:
    replies = [
        PingReply(
            sequence=index,
            status=PingReplyStatus.SUCCESS if latency is not None else PingReplyStatus.TIMEOUT,
            latency_ms=latency,
            error=None if latency is not None else "请求超时。",
        )
        for index, latency in enumerate(latencies, start=1)
    ]
    return build_stats(target, target, replies)


class FakeProvider:
    def __init__(self, stats: PingStats | None = None, error: Exception | None = None) -> None:
        self.stats = stats
        self.error = error
        self.calls: list[tuple[str, int, int]] = []

    def ping(
        self,
        target: str,
        count: int,
        timeout_ms: int,
        *,
        is_cancelled: object = None,
    ) -> PingStats:
        self.calls.append((target, count, timeout_ms))
        if self.error is not None:
            raise self.error
        if self.stats is None:
            return _stats(target, [1.0] * count)
        return self.stats


def test_build_stats_aggregates() -> None:
    stats = _stats("127.0.0.1", [1.0, 2.0, None, 4.0])
    assert stats.sent == 4
    assert stats.received == 3
    assert stats.lost == 1
    assert stats.loss_percent == 25.0
    assert stats.min_latency_ms == 1.0
    assert stats.max_latency_ms == 4.0
    assert stats.avg_latency_ms == pytest.approx(7.0 / 3.0)


def test_tool_success_via_provider() -> None:
    fake = FakeProvider(stats=_stats("192.168.1.1", [1.2, 1.4, 1.3, 1.5]))
    result = PingTool(provider=fake).run(
        {"target": "192.168.1.1", "count": 4, "timeout": 1000},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert "成功 4/4" in result.summary
    assert len(result.data) == 4
    assert result.metadata["display"]["table"]["columns"][0]["label"] == "序号"
    assert result.findings == []
    assert fake.calls == [("192.168.1.1", 4, 1000)]


def test_tool_partial_loss_finding() -> None:
    fake = FakeProvider(stats=_stats("192.168.1.1", [1.0, None, 1.0, None]))
    result = PingTool(provider=fake).run(
        {"target": "192.168.1.1", "count": 4, "timeout": 1000},
        _context(),
    )
    assert "成功 2/4" in result.summary
    assert result.findings[0].title == "存在丢包"
    assert result.findings[0].kind.value == "FACT"


def test_tool_invalid_params_fail_gracefully() -> None:
    result = PingTool(provider=FakeProvider()).run(
        {"target": "192.168.1.1", "count": 50, "timeout": 1000},
        _context(),
    )
    assert result.status is ResultStatus.FAILED
    assert "Ping 参数无效" in result.summary


def test_tool_provider_error_fails_gracefully() -> None:
    fake = FakeProvider(
        error=ToolInputError("ipv6", user_message="当前版本 Ping 仅支持 IPv4 目标。")
    )
    result = PingTool(provider=fake).run(
        {"target": "2001:db8::1", "count": 4, "timeout": 1000},
        _context(),
    )
    assert result.status is ResultStatus.FAILED
    assert result.summary == "当前版本 Ping 仅支持 IPv4 目标。"


def test_tool_cancellation_propagates() -> None:
    fake = FakeProvider(error=TaskCancelledError())
    with pytest.raises(TaskCancelledError):
        PingTool(provider=fake).run(
            {"target": "127.0.0.1", "count": 4, "timeout": 1000},
            _context(),
        )


def test_windows_provider_input_validation() -> None:
    provider = WindowsPingProvider()
    with pytest.raises(ToolInputError):
        provider.ping("", 4, 1000)
    with pytest.raises(ToolInputError):
        provider.ping("example.com", 4, 1000)
    with pytest.raises(ToolInputError):
        provider.ping("2001:db8::1", 4, 1000)
    with pytest.raises(ToolInputError):
        provider.ping("127.0.0.1", 0, 1000)
    with pytest.raises(ToolInputError):
        provider.ping("127.0.0.1", 11, 1000)


@pytest.mark.skipif(platform.system() != "Windows", reason="icmp.dll only exists on Windows")
def test_windows_provider_pings_loopback() -> None:
    stats = WindowsPingProvider().ping("127.0.0.1", count=2, timeout_ms=2000)
    assert stats.sent == 2
    assert stats.received == 2
    assert stats.avg_latency_ms is not None
