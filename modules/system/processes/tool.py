"""ProcessesTool: read-only process enumeration."""

from __future__ import annotations

from typing import Any, ClassVar

from core.finding import Finding, FindingKind, Severity
from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext
from core.tool_definition import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolParameters,
)
from infrastructure.filesystem import human_size
from infrastructure.system import ProcessProvider

DISPLAY_SPEC: dict[str, Any] = {
    "title": "进程列表",
    "table": {
        "columns": [
            {"field": "pid", "label": "PID"},
            {"field": "name", "label": "名称"},
            {"field": "username", "label": "用户"},
            {"field": "cpu_percent", "label": "CPU%"},
            {"field": "memory_percent", "label": "内存%"},
            {"field": "rss", "label": "RSS"},
            {"field": "status", "label": "状态"},
            {"field": "exe", "label": "路径"},
        ]
    },
}


class ProcessesTool(BaseTool):
    """进程查看：只读枚举进程信息（单个进程失败不影响整个列表）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="system.processes",
        name="进程查看",
        category=ToolCategory.SYSTEM,
        icon="system",
        description="只读查看进程 PID/名称/用户/CPU/内存/路径（不提供结束进程等修改能力）。",
        parameters=[
            ToolParameter(
                name="filter",
                label="搜索（名称/PID/路径/用户）",
                placeholder="留空显示全部，如 python 或 1234",
            )
        ],
    )

    def __init__(self, provider: ProcessProvider | None = None) -> None:
        self._provider = provider or ProcessProvider()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        keyword = str(params.get("filter", "")).strip().lower()
        context.info(f"{self.id} 开始枚举进程")
        processes, denied = self._provider.list_processes()
        rows = [
            {
                "pid": process.pid,
                "name": process.name,
                "username": process.username,
                "cpu_percent": process.cpu_percent,
                "memory_percent": process.memory_percent,
                "rss": human_size(process.rss),
                "status": process.status,
                "exe": process.exe,
            }
            for process in processes
            if not keyword
            or keyword in process.name.lower()
            or keyword == str(process.pid)
            or keyword in process.username.lower()
            or keyword in process.exe.lower()
        ]
        findings: list[Finding] = []
        if denied:
            findings.append(
                Finding(
                    title="部分进程信息无法读取",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=(
                        f"有 {denied} 个进程信息读取失败（Access Denied 等），"
                        "可能需要更高权限，其余进程已正常显示。"
                    ),
                    evidence=f"denied={denied}",
                    source=self.id,
                )
            )
        context.info(f"{self.id} 完成：{len(processes)} 个进程（{denied} 个受限）")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"共 {len(processes)} 个进程（显示 {len(rows)} 个）。",
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
