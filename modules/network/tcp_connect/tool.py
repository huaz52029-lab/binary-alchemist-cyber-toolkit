"""TCPConnectTool: single TCP connection reachability check."""

from __future__ import annotations

from typing import ClassVar

from pydantic import ValidationError

from core.exceptions import ToolInputError, to_user_message
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
from infrastructure.network import ProbeStatus, TcpClient
from modules.network.tcp_connect.models import DISPLAY_SPEC, TCPConnectInput


class TCPConnectTool(BaseTool):
    """TCP 连接检测：检测目标端口是否能建立 TCP 连接。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="network.tcp_connect",
        name="TCP 连接检测",
        category=ToolCategory.NETWORK,
        icon="tcp",
        description="检测指定目标端口能否建立 TCP 连接（连通性事实，非服务判定）。",
        version="1.0.0",
        tags=["tcp", "connect", "reachability"],
        parameters=[
            ToolParameter(name="target", label="目标", placeholder="192.168.1.1 或 example.com"),
            ToolParameter(
                name="port",
                label="端口",
                kind=ToolParameterKind.INTEGER,
                default=80,
                minimum=1,
                maximum=65535,
            ),
            ToolParameter(
                name="timeout",
                label="超时(ms)",
                kind=ToolParameterKind.INTEGER,
                default=3000,
                minimum=100,
                maximum=10000,
            ),
        ],
    )

    def __init__(self, client: TcpClient | None = None) -> None:
        self._client = client or TcpClient(default_timeout=3.0, max_timeout=10.0)

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        try:
            model = TCPConnectInput.model_validate(dict(params))
        except ValidationError as exc:
            context.error(f"{self.id} 参数校验失败：{exc}")
            return context.make_result(
                ResultStatus.FAILED,
                "TCP 检测参数无效：端口需 1-65535，超时需 100-10000ms。",
            )
        context.info(f"{self.id} 开始检测 {model.target}:{model.port}（超时 {model.timeout}ms）")
        try:
            probe = self._client.check_port(
                model.target,
                model.port,
                model.timeout / 1000.0,
                is_cancelled=lambda: context.is_cancelled,
            )
        except ToolInputError as exc:
            context.error(f"{self.id} 失败：{exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        except OSError as exc:
            context.error(f"{self.id} 失败：{exc}")
            return context.make_result(ResultStatus.FAILED, to_user_message(exc))
        data = {
            "target": probe.host,
            "port": probe.port,
            "family": probe.family,
            "resolved_address": probe.resolved_address,
            "status": probe.status.value,
            "latency_ms": round(probe.latency_ms, 2) if probe.latency_ms is not None else None,
            "error": probe.error,
        }
        status_labels = {
            ProbeStatus.OPEN: "开放",
            ProbeStatus.CLOSED: "关闭",
            ProbeStatus.TIMEOUT: "超时",
            ProbeStatus.ERROR: "错误",
        }
        summary = f"端口 {model.port} {status_labels[probe.status]}"
        if probe.latency_ms is not None:
            summary += f"（{probe.latency_ms:.1f}ms）"
        context.info(f"{self.id} 完成：{summary}")
        findings: list[Finding] = []
        if probe.status is ProbeStatus.OPEN:
            findings.append(
                Finding(
                    title="端口可连通",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=(
                        "在当前测试条件下 TCP 连接成功建立。这只说明端口可连通，"
                        "不代表服务类型、版本或安全状态。"
                    ),
                    evidence=f"{probe.host}:{probe.port} OPEN",
                    source=self.id,
                )
            )
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=[data],
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
