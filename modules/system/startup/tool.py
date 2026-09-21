"""StartupTool: read-only startup entry analysis."""

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
from infrastructure.system import StartupProvider
from infrastructure.system.windows_provider import command_has_script_host

DISPLAY_SPEC: dict[str, Any] = {
    "title": "启动项分析",
    "table": {
        "columns": [
            {"field": "source", "label": "来源"},
            {"field": "name", "label": "名称"},
            {"field": "command", "label": "命令"},
            {"field": "user_scope", "label": "范围"},
            {"field": "exists", "label": "存在状态"},
        ]
    },
}


def _startup_findings(rows: list[dict[str, Any]], source: str) -> list[Finding]:
    findings: list[Finding] = []
    for row in rows:
        command = row["command"]
        if row["exists"] is False:
            findings.append(
                Finding(
                    title="启动项路径不存在",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description=(
                        f"启动项「{row['name']}」的可执行路径当前无法确认存在，需结合实际环境判断。"
                    ),
                    evidence=f"name={row['name']}",
                    source=source,
                )
            )
        if command_has_script_host(command):
            findings.append(
                Finding(
                    title="启动命令包含脚本宿主",
                    severity=Severity.INFO,
                    kind=FindingKind.HEURISTIC,
                    description=(
                        f"启动项「{row['name']}」的命令包含 powershell/wscript/cscript/mshta 等"
                        "脚本宿主。发现脚本宿主不等于恶意，仅作为分析线索。"
                    ),
                    evidence=f"name={row['name']}",
                    source=source,
                )
            )
    return findings


class StartupTool(BaseTool):
    """启动项分析：只读查看 Run/RunOnce 注册表键与 Startup 目录。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="system.startup",
        name="启动项分析",
        category=ToolCategory.SYSTEM,
        icon="system",
        description="只读查看 HKCU/HKLM 的 Run/RunOnce 与 Startup 目录；不提供修改能力。",
    )

    def __init__(self, provider: StartupProvider | None = None) -> None:
        self._provider = provider or StartupProvider()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        context.info(f"{self.id} 开始读取启动项")
        entries, errors = self._provider.list_startup_entries()
        rows = [
            {
                "source": entry.source,
                "name": entry.name,
                "command": entry.command,
                "user_scope": entry.user_scope,
                "exists": (
                    "存在"
                    if entry.exists is True
                    else "无法确认"
                    if entry.exists is None
                    else "不存在"
                ),
            }
            for entry in entries
        ]
        findings = _startup_findings(
            [
                {"name": entry.name, "command": entry.command, "exists": entry.exists}
                for entry in entries
            ],
            self.id,
        )
        if rows:
            findings.append(
                Finding(
                    title="检测到用户启动项",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=f"发现 {len(rows)} 个启动项，仅作为本机状态信息。",
                    evidence=f"startup_count={len(rows)}",
                    source=self.id,
                )
            )
        if errors:
            findings.append(
                Finding(
                    title="部分启动项来源无法访问",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=f"有 {len(errors)} 个启动项来源读取失败。",
                    evidence=f"errors={len(errors)}",
                    source=self.id,
                )
            )
        context.info(f"{self.id} 完成：{len(entries)} 个启动项")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"共发现 {len(entries)} 个启动项（只读分析）。",
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
