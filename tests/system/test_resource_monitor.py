"""Resource monitor sampling with an injected provider."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.system import MemoryInfo, SystemInfoProvider
from modules.system.resource_monitor import ResourceMonitorTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-mon",
        tool_id="system.resource_monitor",
        logger=logging.getLogger("tests.mon"),
        cancel_event=threading.Event(),
    )


class FakeSystemInfoProvider(SystemInfoProvider):
    def __init__(self) -> None:
        self.sent = 1_000_000
        self.recv = 2_000_000

    def get_cpu_usage(self) -> float | None:
        return 25.0

    def get_memory(self) -> MemoryInfo:
        return MemoryInfo(100, 40, 60, 40.0, 0, 0, 0.0)

    def get_net_counters(self) -> tuple[int, int]:
        return self.sent, self.recv


def test_resource_monitor_baseline_and_speeds() -> None:
    provider = FakeSystemInfoProvider()
    # Each sampling round increments counters by 1MB/s sent and 2MB/s received.
    original_get = provider.get_net_counters
    calls = {"n": 0}

    def get_net_counters() -> tuple[int, int]:
        calls["n"] += 1
        sent, recv = original_get()
        provider.sent += 1_000_000
        provider.recv += 2_000_000
        return sent, recv

    provider.get_net_counters = get_net_counters  # type: ignore[method-assign]
    result = ResourceMonitorTool(provider=provider).run(
        {"samples": 3, "interval_ms": 500},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    rows = result.data
    assert len(rows) == 3
    assert rows[0]["upload_bps"] == "-"
    assert rows[0]["download_bps"] == "-"
    assert rows[1]["upload_bps"] != "-"
    assert rows[1]["cpu"] == 25.0
    assert rows[1]["memory"] == 40.0
