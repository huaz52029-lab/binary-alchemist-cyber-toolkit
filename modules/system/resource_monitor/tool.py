"""ResourceMonitorTool: sampled CPU/memory/network trend series."""

from __future__ import annotations

import time
from typing import Any, ClassVar

from core.exceptions import TaskCancelledError
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
from infrastructure.system import SystemInfoProvider

DISPLAY_SPEC: dict[str, Any] = {
    "title": "资源监控采样",
    "table": {
        "columns": [
            {"field": "sample", "label": "采样"},
            {"field": "cpu", "label": "CPU%"},
            {"field": "memory", "label": "内存%"},
            {"field": "upload_bps", "label": "上传速度"},
            {"field": "download_bps", "label": "下载速度"},
        ]
    },
}


def _rate_string(bps: float | None) -> str:
    if bps is None:
        return "-"
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if bps < 1024 or unit == "GB/s":
            return f"{bps:.1f} {unit}"
        bps /= 1024
    return "-"


class ResourceMonitorTool(BaseTool):
    """资源监控：按固定间隔采样 CPU/内存/网络速度，形成趋势序列（只读）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="system.resource_monitor",
        name="资源监控",
        category=ToolCategory.SYSTEM,
        icon="system",
        description="按固定间隔采样 CPU/内存使用率与网络上下行速度，生成趋势数据（只读）。",
        parameters=[
            ToolParameter(
                name="samples",
                label="采样次数",
                kind=ToolParameterKind.INTEGER,
                default=5,
                minimum=3,
                maximum=60,
            ),
            ToolParameter(
                name="interval_ms",
                label="间隔(ms)",
                kind=ToolParameterKind.INTEGER,
                default=1000,
                minimum=500,
                maximum=5000,
            ),
        ],
    )

    def __init__(self, provider: SystemInfoProvider | None = None) -> None:
        self._provider = provider or SystemInfoProvider()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        samples = int(params.get("samples", 5))
        interval = int(params.get("interval_ms", 1000)) / 1000.0
        context.info(f"{self.id} 开始采样：{samples} 次，间隔 {interval}s")
        previous_sent, previous_recv = self._provider.get_net_counters()
        previous_time = time.perf_counter()
        rows: list[dict[str, Any]] = []
        for index in range(1, samples + 1):
            if context.is_cancelled:
                raise TaskCancelledError()
            cpu = self._provider.get_cpu_usage()
            memory = self._provider.get_memory()
            now = time.perf_counter()
            sent, received = self._provider.get_net_counters()
            elapsed = now - previous_time
            if index == 1:
                upload = download = None  # first sample establishes the baseline
            else:
                upload = (sent - previous_sent) / elapsed if elapsed > 0 else None
                download = (received - previous_recv) / elapsed if elapsed > 0 else None
            rows.append(
                {
                    "sample": index,
                    "cpu": round(cpu, 1) if cpu is not None else "N/A",
                    "memory": round(memory.percent, 1),
                    "upload_bps": _rate_string(upload),
                    "download_bps": _rate_string(download),
                }
            )
            context.set_progress(
                index / samples * 100.0,
                f"采样 {index}/{samples}",
            )
            previous_sent, previous_recv = sent, received
            previous_time = now
            if index < samples:
                # Cancellable sleep between samples.
                deadline = time.monotonic() + interval
                while time.monotonic() < deadline:
                    if context.is_cancelled:
                        raise TaskCancelledError()
                    time.sleep(0.05)
        context.info(f"{self.id} 完成：{samples} 次采样")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"完成 {samples} 次采样（间隔 {interval}s），首行为基线。",
            data=rows,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
