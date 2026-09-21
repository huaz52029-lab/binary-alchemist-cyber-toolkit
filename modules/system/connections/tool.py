"""ConnectionsTool: TCP/UDP connections and listening ports (read-only)."""

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
from infrastructure.system import ConnectionProvider

DISPLAY_SPEC: dict[str, Any] = {
    "title": "网络连接",
    "table": {
        "columns": [
            {"field": "protocol", "label": "协议"},
            {"field": "local_address", "label": "本地地址"},
            {"field": "local_port", "label": "本地端口"},
            {"field": "remote_address", "label": "远端地址"},
            {"field": "remote_port", "label": "远端端口"},
            {"field": "status", "label": "状态"},
            {"field": "pid", "label": "PID"},
            {"field": "process_name", "label": "进程"},
        ]
    },
}


class ConnectionsTool(BaseTool):
    """网络连接：查看本机 TCP/UDP 连接与监听端口（只读状态分析）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="system.connections",
        name="网络连接",
        category=ToolCategory.SYSTEM,
        icon="system",
        description="查看本机 TCP/UDP 连接与监听端口，仅作状态展示，不做漏洞判定。",
        parameters=[
            ToolParameter(
                name="filter",
                label="搜索（协议/状态/端口/地址/PID/进程）",
                placeholder="如 443 或 ESTABLISHED",
            )
        ],
    )

    def __init__(self, provider: ConnectionProvider | None = None) -> None:
        self._provider = provider or ConnectionProvider()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        keyword = str(params.get("filter", "")).strip().lower()
        context.info(f"{self.id} 开始枚举网络连接")
        connections = self._provider.list_connections()
        rows = [
            {
                "protocol": connection.protocol,
                "local_address": connection.local_address,
                "local_port": connection.local_port,
                "remote_address": connection.remote_address,
                "remote_port": connection.remote_port,
                "status": connection.status,
                "pid": connection.pid if connection.pid is not None else "-",
                "process_name": connection.process_name,
            }
            for connection in connections
            if not keyword
            or keyword in connection.protocol.lower()
            or keyword in connection.status.lower()
            or keyword == str(connection.local_port)
            or keyword == str(connection.remote_port)
            or keyword in connection.remote_address.lower()
            or keyword in connection.process_name.lower()
        ]
        listening = sum(connection.status == "LISTEN" for connection in connections)
        findings: list[Finding] = []
        if listening:
            findings.append(
                Finding(
                    title="存在监听端口",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=(
                        f"当前有 {listening} 个监听端口，仅表示本机存在监听状态，不构成漏洞判定。"
                    ),
                    evidence=f"listening={listening}",
                    source=self.id,
                )
            )
        context.info(f"{self.id} 完成：{len(connections)} 条连接（监听 {listening}）")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"共 {len(connections)} 条连接，其中监听 {listening} 个。",
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
