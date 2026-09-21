"""PingTool: ICMP connectivity and latency testing."""

from __future__ import annotations

from typing import ClassVar

from pydantic import ValidationError

from core.exceptions import NetworkError, ToolInputError, to_user_message
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
from infrastructure.network import PingProvider, WindowsPingProvider
from modules.network.ping.models import DISPLAY_SPEC, PingInput


class PingTool(BaseTool):
    """Ping 测试：通过系统 ICMP 检测目标连通性与延迟。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="network.ping",
        name="Ping 测试",
        category=ToolCategory.NETWORK,
        icon="ping",
        description="通过系统 ICMP Ping 检测目标主机连通性与延迟。",
        version="1.0.0",
        tags=["ping", "icmp", "latency"],
        parameters=[
            ToolParameter(name="target", label="目标地址", placeholder="192.168.1.1"),
            ToolParameter(
                name="count",
                label="次数",
                kind=ToolParameterKind.INTEGER,
                default=4,
                minimum=1,
                maximum=10,
            ),
            ToolParameter(
                name="timeout",
                label="超时(ms)",
                kind=ToolParameterKind.INTEGER,
                default=1000,
                minimum=100,
                maximum=5000,
            ),
        ],
    )

    def __init__(self, provider: PingProvider | None = None) -> None:
        self._provider: PingProvider = provider or WindowsPingProvider()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        try:
            model = PingInput.model_validate(dict(params))
        except ValidationError as exc:
            context.error(f"{self.id} 参数校验失败：{exc}")
            return context.make_result(
                ResultStatus.FAILED,
                "Ping 参数无效：次数需 1-10，超时需 100-5000ms，目标不能为空。",
            )
        context.info(
            f"{self.id} 开始测试 {model.target}（次数 {model.count}，超时 {model.timeout}ms）"
        )
        try:
            stats = self._provider.ping(
                model.target,
                model.count,
                model.timeout,
                is_cancelled=lambda: context.is_cancelled,
            )
        except ToolInputError as exc:
            context.error(f"{self.id} 失败：{exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        except (OSError, NetworkError) as exc:
            context.error(f"{self.id} 失败：{exc}")
            return context.make_result(ResultStatus.FAILED, to_user_message(exc))
        summary = f"成功 {stats.received}/{stats.sent}，丢包 {stats.loss_percent:.1f}%"
        if stats.avg_latency_ms is not None:
            summary += (
                f"，平均 {stats.avg_latency_ms:.1f}ms"
                f"（最小 {stats.min_latency_ms:.1f}，最大 {stats.max_latency_ms:.1f}）"
            )
        context.info(f"{self.id} 完成：成功 {stats.received}/{stats.sent}")
        findings: list[Finding] = []
        if stats.lost > 0:
            findings.append(
                Finding(
                    title="存在丢包",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=(
                        f"{stats.received}/{stats.sent} 个请求获得响应；"
                        "目标不可达、ICMP 被过滤或链路拥塞都可能导致丢包。"
                    ),
                    evidence=f"loss_percent={stats.loss_percent:.1f}%",
                    source=self.id,
                )
            )
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=[
                {
                    "sequence": reply.sequence,
                    "status": reply.status.value,
                    "latency_ms": reply.latency_ms,
                    "error": reply.error,
                }
                for reply in stats.replies
            ],
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
