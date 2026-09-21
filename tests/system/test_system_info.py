"""System info tool with an injected provider."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.system import (
    DiskInfo,
    MemoryInfo,
    SystemInfoData,
    SystemInfoProvider,
)
from modules.system.system_info import SystemInfoTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-sinfo",
        tool_id="system.system_info",
        logger=logging.getLogger("tests.sinfo"),
        cancel_event=threading.Event(),
    )


class FakeSystemInfoProvider(SystemInfoProvider):
    def get_system_info(self) -> SystemInfoData:
        return SystemInfoData(
            os_name="Windows",
            os_version="10",
            os_build="19045",
            architecture="64bit",
            machine="AMD64",
            hostname="TEST-PC",
            username="tester",
            python_version="3.13.0",
            processor="Test CPU",
            logical_cpus=8,
            physical_cpus=4,
            boot_time="2026-09-20T00:00:00+00:00",
            uptime_seconds=90061,
            disks=(DiskInfo("C:", "C:\\", "NTFS", 1000, 420, 580, 42.0),),
        )

    def get_memory(self) -> MemoryInfo:
        return MemoryInfo(16 * 1024**3, 6 * 1024**3, 10 * 1024**3, 37.5, 0, 0, 0.0)

    def get_cpu_usage(self) -> float | None:
        return 23.4


def test_system_info_rows() -> None:
    result = SystemInfoTool(provider=FakeSystemInfoProvider()).run({}, _context())
    assert result.status is ResultStatus.SUCCESS
    rows = {(row["section"], row["item"]): row["value"] for row in result.data}
    assert rows[("操作系统", "系统")] == "Windows"
    assert rows[("CPU", "当前使用率")] == "23.4%"
    assert rows[("内存", "使用率")] == "37.5%"
    assert any(section.startswith("磁盘") for section, _item in rows)
    assert "1天" in rows[("启动", "运行时长")]
