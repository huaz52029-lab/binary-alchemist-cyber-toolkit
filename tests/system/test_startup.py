"""Startup tool with injected provider and finding logic."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.system import StartupEntry, StartupProvider
from modules.system.startup import StartupTool, _startup_findings


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-startup",
        tool_id="system.startup",
        logger=logging.getLogger("tests.startup"),
        cancel_event=threading.Event(),
    )


class FakeStartupProvider(StartupProvider):
    def __init__(self) -> None:
        self.entries = [
            StartupEntry("HKCU Run", "App", r'"C:\Program Files\App\app.exe"', "用户", True),
            StartupEntry("HKLM Run", "Update", "powershell -enc AAA", "系统", None),
            StartupEntry("HKCU RunOnce", "Gone", r"C:\missing\tool.exe", "用户", False),
        ]
        self.errors: list[str] = []

    def list_startup_entries(self) -> tuple[list[StartupEntry], list[str]]:
        return self.entries, self.errors


def test_startup_rows_and_findings() -> None:
    provider = FakeStartupProvider()
    result = StartupTool(provider=provider).run({}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert len(result.data) == 3
    assert result.data[2]["exists"] == "不存在"
    titles = {finding.title for finding in result.findings}
    assert "启动项路径不存在" in titles
    assert "启动命令包含脚本宿主" in titles
    assert "检测到用户启动项" in titles


def test_startup_finding_logic() -> None:
    rows = [
        {"name": "x", "command": r"C:\missing\x.exe", "exists": False},
        {"name": "y", "command": "wscript C:\\x\\y.vbs", "exists": True},
        {"name": "z", "command": '"C:\\Program Files\\Z\\z.exe"', "exists": True},
    ]
    findings = _startup_findings(rows, "system.startup")
    titles = {finding.title for finding in findings}
    assert titles == {"启动项路径不存在", "启动命令包含脚本宿主"}
