"""SystemAnalyzerTool: composite read-only system security summary."""

from __future__ import annotations

from typing import Any, ClassVar

from core.finding import Finding, FindingKind, Severity
from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext
from core.tool_definition import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameters,
)
from infrastructure.system import (
    ConnectionProvider,
    ProcessProvider,
    StartupProvider,
    SystemInfoProvider,
    WindowsServiceProvider,
)
from modules.system.environment.tool import redact_environment_value
from modules.system.services.tool import _service_findings
from modules.system.startup.tool import _startup_findings

DISPLAY_SPEC: dict[str, Any] = {
    "title": "系统安全分析",
    "table": {
        "columns": [
            {"field": "section", "label": "分类"},
            {"field": "item", "label": "项目"},
            {"field": "value", "label": "值"},
        ]
    },
}


class SystemAnalyzerTool(BaseTool):
    """系统安全分析：汇总系统信息、进程、连接、服务、启动项、用户与环境（只读）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="system.analyzer",
        name="系统安全分析",
        category=ToolCategory.SYSTEM,
        icon="system",
        description="只读汇总本机系统安全状态；子模块失败不影响其他部分结果。",
    )

    def __init__(
        self,
        *,
        system_provider: SystemInfoProvider | None = None,
        process_provider: ProcessProvider | None = None,
        connection_provider: ConnectionProvider | None = None,
        service_provider: WindowsServiceProvider | None = None,
        startup_provider: StartupProvider | None = None,
    ) -> None:
        self._system_provider = system_provider or SystemInfoProvider()
        self._process_provider = process_provider or ProcessProvider()
        self._connection_provider = connection_provider or ConnectionProvider()
        self._service_provider = service_provider or WindowsServiceProvider()
        self._startup_provider = startup_provider or StartupProvider()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        context.info(f"{self.id} 开始综合分析")
        rows: list[dict[str, Any]] = []
        findings: list[Finding] = []
        failures: list[str] = []

        try:
            info = self._system_provider.get_system_info()
            memory = self._system_provider.get_memory()
            rows.extend(
                [
                    {
                        "section": "系统",
                        "item": "操作系统",
                        "value": f"{info.os_name} {info.os_version}",
                    },
                    {"section": "系统", "item": "主机名", "value": info.hostname},
                    {"section": "系统", "item": "当前用户", "value": info.username},
                    {"section": "系统", "item": "内存使用率", "value": f"{memory.percent:.1f}%"},
                ]
            )
        except Exception as exc:
            failures.append(f"系统信息：{exc}")

        try:
            processes, denied = self._process_provider.list_processes()
            rows.append({"section": "进程", "item": "活动进程", "value": str(len(processes))})
            if denied:
                findings.append(
                    Finding(
                        title="部分进程信息无法读取",
                        severity=Severity.INFO,
                        kind=FindingKind.FACT,
                        description=f"{denied} 个进程读取受限，可能需要更高权限。",
                        evidence=f"denied={denied}",
                        source=self.id,
                    )
                )
        except Exception as exc:
            failures.append(f"进程：{exc}")

        try:
            connections = self._connection_provider.list_connections()
            listening = sum(c.status == "LISTEN" for c in connections)
            established = sum(c.status == "ESTABLISHED" for c in connections)
            rows.append({"section": "网络", "item": "监听端口", "value": str(listening)})
            rows.append({"section": "网络", "item": "ESTABLISHED 连接", "value": str(established)})
            if listening:
                findings.append(
                    Finding(
                        title="存在多个监听端口",
                        severity=Severity.INFO,
                        kind=FindingKind.FACT,
                        description=f"当前有 {listening} 个监听端口，仅作状态展示。",
                        evidence=f"listening={listening}",
                        source=self.id,
                    )
                )
        except Exception as exc:
            failures.append(f"网络连接：{exc}")

        try:
            services, service_errors = self._service_provider.list_services()
            running = sum(s.status == "RUNNING" for s in services)
            rows.append(
                {"section": "服务", "item": "运行服务", "value": f"{running}/{len(services)}"}
            )
            service_rows = [
                {"name": s.name, "binary_path": s.binary_path or "N/A"} for s in services
            ]
            findings.extend(_service_findings(service_rows, self.id))
            if service_errors:
                failures.append(f"服务（{len(service_errors)} 个受限）")
        except Exception as exc:
            failures.append(f"服务：{exc}")

        try:
            startup_entries, startup_errors = self._startup_provider.list_startup_entries()
            rows.append({"section": "启动项", "item": "数量", "value": str(len(startup_entries))})
            startup_rows = [
                {
                    "name": e.name,
                    "command": e.command,
                    "exists": e.exists,
                }
                for e in startup_entries
            ]
            findings.extend(_startup_findings(startup_rows, self.id))
            if startup_entries:
                findings.append(
                    Finding(
                        title="检测到用户启动项",
                        severity=Severity.INFO,
                        kind=FindingKind.FACT,
                        description=f"发现 {len(startup_entries)} 个启动项，仅作为状态信息。",
                        evidence=f"startup_count={len(startup_entries)}",
                        source=self.id,
                    )
                )
            if startup_errors:
                failures.append(f"启动项（{len(startup_errors)} 个来源受限）")
        except Exception as exc:
            failures.append(f"启动项：{exc}")

        try:
            import os

            import psutil

            user_count = len(psutil.users())
            env_count = len(os.environ)
            sensitive_env = sum(
                redact_environment_value(name, value)[1] for name, value in os.environ.items()
            )
            rows.append({"section": "用户", "item": "登录会话", "value": str(user_count)})
            rows.append(
                {
                    "section": "环境",
                    "item": "环境变量",
                    "value": f"{env_count} 个（{sensitive_env} 个敏感已脱敏）",
                }
            )
        except Exception as exc:
            failures.append(f"用户/环境：{exc}")

        if failures:
            findings.append(
                Finding(
                    title="部分系统信息无法获取",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=f"以下子模块读取失败：{', '.join(failures)}。其余结果仍然有效。",
                    evidence=f"failed_modules={len(failures)}",
                    source=self.id,
                )
            )
        status = ResultStatus.PARTIAL if failures else ResultStatus.SUCCESS
        summary = (
            f"活动进程 {next((r['value'] for r in rows if r['item'] == '活动进程'), '?')} · "
            f"监听端口 {next((r['value'] for r in rows if r['item'] == '监听端口'), '?')} · "
            f"提示 {len(findings)} 项（只读分析）"
        )
        context.info(
            f"{self.id} 完成：{status.value}，失败模块 {len(failures)}，Finding {len(findings)}"
        )
        return context.make_result(
            status,
            summary,
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
