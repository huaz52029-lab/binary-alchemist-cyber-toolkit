"""System analyzer composite behavior, including partial failure."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.system import (
    ConnectionInfo,
    ConnectionProvider,
    ProcessInfo,
    ProcessProvider,
    ServiceInfo,
    StartupEntry,
    StartupProvider,
    SystemInfoData,
    SystemInfoProvider,
    WindowsServiceProvider,
)
from modules.system.analyzer import SystemAnalyzerTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-sana",
        tool_id="system.analyzer",
        logger=logging.getLogger("tests.sana"),
        cancel_event=threading.Event(),
    )


class _OkSystem(SystemInfoProvider):
    def get_system_info(self) -> SystemInfoData:
        return SystemInfoData(
            os_name="Windows",
            os_version="10",
            os_build="1",
            architecture="64bit",
            machine="AMD64",
            hostname="PC",
            username="user",
            python_version="3.13",
            processor="CPU",
            logical_cpus=4,
            physical_cpus=2,
            boot_time="2026-01-01T00:00:00+00:00",
            uptime_seconds=100,
        )

    def get_memory(self):  # type: ignore[no-untyped-def]
        from infrastructure.system import MemoryInfo

        return MemoryInfo(100, 50, 50, 50.0, 0, 0, 0.0)


class _OkProcesses(ProcessProvider):
    def list_processes(self):  # type: ignore[no-untyped-def]
        return [ProcessInfo(1, "a", "u", 0.0, 0.0, 0, "running", "x", "x")], 0


class _OkConnections(ConnectionProvider):
    def list_connections(self):  # type: ignore[no-untyped-def]
        return [
            ConnectionInfo("TCP", "127.0.0.1", 443, "", 0, "LISTEN", 1, "a"),
            ConnectionInfo("TCP", "127.0.0.1", 53000, "1.1.1.1", 443, "ESTABLISHED", 2, "b"),
        ]


class _OkServices(WindowsServiceProvider):
    def list_services(self):  # type: ignore[no-untyped-def]
        return [ServiceInfo("s", "S", "RUNNING", "AUTO", "LocalSystem", "", r'"C:\x.exe"')], []


class _OkStartup(StartupProvider):
    def list_startup_entries(self):  # type: ignore[no-untyped-def]
        return [StartupEntry("HKCU Run", "A", r'"C:\A.exe"', "用户", True)], []


class _BrokenServices(WindowsServiceProvider):
    def list_services(self):  # type: ignore[no-untyped-def]
        raise RuntimeError("services unavailable")


def _tool(services: WindowsServiceProvider | None = None) -> SystemAnalyzerTool:
    return SystemAnalyzerTool(
        system_provider=_OkSystem(),
        process_provider=_OkProcesses(),
        connection_provider=_OkConnections(),
        service_provider=services or _OkServices(),
        startup_provider=_OkStartup(),
    )


def test_analyzer_success() -> None:
    result = _tool().run({}, _context())
    assert result.status is ResultStatus.SUCCESS
    rows = {row["item"]: row["value"] for row in result.data}
    assert rows["活动进程"] == "1"
    assert rows["监听端口"] == "1"
    assert rows["运行服务"] == "1/1"
    assert any(finding.title == "存在多个监听端口" for finding in result.findings)
    assert any(finding.title == "检测到用户启动项" for finding in result.findings)


def test_analyzer_partial_when_services_fail() -> None:
    result = _tool(services=_BrokenServices()).run({}, _context())
    assert result.status is ResultStatus.PARTIAL
    rows = {row["item"]: row["value"] for row in result.data}
    assert rows["活动进程"] == "1"  # processes still returned
    assert any(finding.title == "部分系统信息无法获取" for finding in result.findings)
