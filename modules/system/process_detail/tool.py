"""ProcessDetailTool: read-only details for one process."""

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
    ToolParameterKind,
    ToolParameters,
)
from infrastructure.filesystem import human_size
from infrastructure.system import ProcessProvider

DISPLAY_SPEC: dict[str, Any] = {
    "title": "进程详细信息",
    "sections": [
        {
            "title": "基本信息",
            "items": [
                {"field": "pid", "label": "PID"},
                {"field": "name", "label": "名称"},
                {"field": "username", "label": "用户"},
                {"field": "status", "label": "状态"},
                {"field": "created", "label": "创建时间"},
            ],
        },
        {
            "title": "资源",
            "items": [
                {"field": "cpu_percent", "label": "CPU%"},
                {"field": "memory_percent", "label": "内存%"},
                {"field": "rss", "label": "RSS"},
                {"field": "num_threads", "label": "线程数"},
            ],
        },
        {
            "title": "路径与命令行",
            "items": [
                {"field": "exe", "label": "可执行文件"},
                {"field": "cmdline", "label": "命令行（可能包含敏感信息）"},
                {"field": "cwd", "label": "工作目录"},
                {"field": "environment_count", "label": "环境变量数量"},
            ],
        },
    ],
}


class ProcessDetailTool(BaseTool):
    """进程详情：只读查看单个进程的线程、命令行、工作目录与环境摘要。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="system.process_detail",
        name="进程详细信息",
        category=ToolCategory.SYSTEM,
        icon="system",
        description="查看单个进程的资源占用、命令行与工作目录（命令行可能包含敏感信息，不写入日志）。",
        parameters=[
            ToolParameter(
                name="pid",
                label="PID",
                kind=ToolParameterKind.INTEGER,
                default=0,
                minimum=0,
                maximum=2_000_000,
            )
        ],
    )

    def __init__(self, provider: ProcessProvider | None = None) -> None:
        self._provider = provider or ProcessProvider()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        pid = int(params.get("pid", 0))
        if pid <= 0:
            return context.make_result(ResultStatus.FAILED, "请输入要查看的进程 PID。")
        context.info(f"{self.id} 查询进程：{pid}")
        detail = self._provider.get_process_detail(pid)
        if detail is None:
            message = "无法读取该进程信息（进程不存在或权限不足）。"
            context.error(f"{self.id} {message}")
            return context.make_result(ResultStatus.FAILED, message)
        row: dict[str, Any] = {
            "pid": detail.pid,
            "name": detail.name,
            "username": detail.username,
            "status": detail.status,
            "created": detail.created,
            "cpu_percent": detail.cpu_percent,
            "memory_percent": detail.memory_percent,
            "rss": human_size(detail.rss),
            "num_threads": detail.num_threads,
            "exe": detail.exe,
            "cmdline": detail.cmdline,
            "cwd": detail.cwd,
            "environment_count": detail.environment_count,
        }
        findings = [
            Finding(
                title="命令行可能包含敏感信息",
                severity=Severity.INFO,
                kind=FindingKind.FACT,
                description=(
                    "命令行参数可能包含 Token、密码或文件路径，请谨慎分享；日志不会记录完整命令行。"
                ),
                evidence=f"cmdline_length={len(detail.cmdline)}",
                source=self.id,
            )
        ]
        context.info(f"{self.id} 完成：{detail.name}，命令行长度 {len(detail.cmdline)}")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"{detail.name}（PID {detail.pid}）详细信息。",
            data=[row],
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
