"""SystemInfoTool: OS, CPU, memory, disk, boot time overview."""

from __future__ import annotations

from typing import Any, ClassVar

from core.exceptions import DependencyMissingError
from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext
from core.tool_definition import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameters,
)
from infrastructure.filesystem import human_size
from infrastructure.system import MemoryInfo, SystemInfoData, SystemInfoProvider

DISPLAY_SPEC: dict[str, Any] = {
    "title": "系统信息",
    "table": {
        "columns": [
            {"field": "section", "label": "分类"},
            {"field": "item", "label": "项目"},
            {"field": "value", "label": "值"},
        ]
    },
}


def _uptime(seconds: int) -> str:
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    return f"{days}天 {hours}小时 {minutes}分钟"


class SystemInfoTool(BaseTool):
    """系统信息：操作系统、CPU、内存、磁盘与运行时长（只读）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="system.system_info",
        name="系统信息",
        category=ToolCategory.SYSTEM,
        icon="system",
        description="查看操作系统版本、CPU/内存/磁盘统计与系统运行时长。",
    )

    def __init__(self, provider: SystemInfoProvider | None = None) -> None:
        self._provider = provider or SystemInfoProvider()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        context.info(f"{self.id} 开始收集系统信息")
        try:
            info: SystemInfoData = self._provider.get_system_info()
            memory: MemoryInfo = self._provider.get_memory()
            cpu_usage = self._provider.get_cpu_usage()
        except DependencyMissingError as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        rows: list[dict[str, Any]] = [
            {"section": "操作系统", "item": "系统", "value": info.os_name},
            {"section": "操作系统", "item": "版本", "value": info.os_version},
            {"section": "操作系统", "item": "构建号", "value": info.os_build},
            {
                "section": "操作系统",
                "item": "架构",
                "value": f"{info.architecture} / {info.machine}",
            },
            {"section": "主机", "item": "主机名", "value": info.hostname},
            {"section": "主机", "item": "当前用户", "value": info.username},
            {"section": "主机", "item": "Python", "value": info.python_version},
            {"section": "CPU", "item": "处理器", "value": info.processor},
            {"section": "CPU", "item": "逻辑核心", "value": str(info.logical_cpus)},
            {"section": "CPU", "item": "物理核心", "value": str(info.physical_cpus or "N/A")},
            {
                "section": "CPU",
                "item": "当前使用率",
                "value": f"{cpu_usage:.1f}%" if cpu_usage is not None else "N/A",
            },
            {"section": "内存", "item": "总内存", "value": human_size(memory.total)},
            {"section": "内存", "item": "已用", "value": human_size(memory.used)},
            {"section": "内存", "item": "可用", "value": human_size(memory.available)},
            {"section": "内存", "item": "使用率", "value": f"{memory.percent:.1f}%"},
            {"section": "Swap", "item": "总量", "value": human_size(memory.swap_total)},
            {"section": "Swap", "item": "使用率", "value": f"{memory.swap_percent:.1f}%"},
            {"section": "启动", "item": "启动时间", "value": info.boot_time},
            {"section": "启动", "item": "运行时长", "value": _uptime(info.uptime_seconds)},
        ]
        for disk in info.disks:
            rows.append(
                {
                    "section": f"磁盘 {disk.mountpoint}",
                    "item": disk.filesystem,
                    "value": (
                        f"{human_size(disk.used)} / {human_size(disk.total)} "
                        f"（{disk.percent:.1f}%）"
                    ),
                }
            )
        context.info(f"{self.id} 完成：{info.os_name}，{info.logical_cpus} 逻辑核心")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"{info.os_name} {info.os_version} · {info.logical_cpus} 逻辑核心 · "
            f"内存 {human_size(memory.total)}。",
            data=rows,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
