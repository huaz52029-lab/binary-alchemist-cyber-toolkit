"""NetworkInterfacesTool: enumerate local network interfaces."""

from __future__ import annotations

from typing import Any, ClassVar

from core.exceptions import DependencyMissingError
from core.finding import Finding, FindingKind, Severity
from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext
from core.tool_definition import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameters,
)
from infrastructure.system import InterfaceInfo, NetworkInterfaceProvider

DISPLAY_SPEC: dict[str, Any] = {
    "title": "网络接口信息",
    "table": {
        "columns": [
            {"field": "name", "label": "接口"},
            {"field": "ipv4", "label": "IPv4"},
            {"field": "ipv6", "label": "IPv6"},
            {"field": "mac", "label": "MAC"},
            {"field": "status", "label": "状态"},
            {"field": "mtu", "label": "MTU"},
        ]
    },
}


def _to_row(info: InterfaceInfo) -> dict[str, Any]:
    return {
        "name": info.name,
        "ipv4": ", ".join(info.ipv4) or "-",
        "ipv6": ", ".join(info.ipv6) or "-",
        "mac": info.mac or "-",
        "status": "UP" if info.up else "DOWN",
        "mtu": info.mtu,
        "bytes_sent": info.bytes_sent,
        "bytes_recv": info.bytes_recv,
        "packets_sent": info.packets_sent,
        "packets_recv": info.packets_recv,
    }


class NetworkInterfacesTool(BaseTool):
    """网络接口：查看本机网络接口的地址、状态与流量统计。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="network.interfaces",
        name="网络接口",
        category=ToolCategory.NETWORK,
        icon="network",
        description="查看本机网络接口的 IPv4/IPv6、MAC、状态、MTU 与流量统计。",
        version="1.0.0",
        tags=["interfaces", "local", "psutil"],
    )

    def __init__(self, provider: NetworkInterfaceProvider | None = None) -> None:
        self._provider = provider or NetworkInterfaceProvider()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        context.info(f"{self.id} 开始读取网络接口信息")
        try:
            interfaces = self._provider.list_interfaces()
        except DependencyMissingError as exc:
            context.error(f"{self.id} 失败：{exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        except OSError as exc:
            context.error(f"{self.id} 读取失败：{exc}")
            return context.make_result(ResultStatus.FAILED, "无法读取网络接口信息。")
        rows = [_to_row(info) for info in interfaces]
        up_count = sum(info.up for info in interfaces)
        findings: list[Finding] = []
        down_names = [info.name for info in interfaces if not info.up]
        if down_names:
            findings.append(
                Finding(
                    title="存在未启用的网络接口",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=f"以下接口处于未启用状态：{', '.join(down_names)}。",
                    evidence=f"down_interfaces={len(down_names)}",
                    source=self.id,
                )
            )
        context.info(f"{self.id} 完成：共 {len(interfaces)} 个接口（UP {up_count}）")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"共 {len(interfaces)} 个网络接口，其中 {up_count} 个处于启用状态",
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
