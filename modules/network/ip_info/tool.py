"""IPInfoTool: the first end-to-end security tool of the platform."""

from __future__ import annotations

from typing import ClassVar

from core.exceptions import ToolInputError
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
from modules.network.ip_info.analyzer import EMPTY_MESSAGE, UNRECOGNIZED_MESSAGE, analyze_ip
from modules.network.ip_info.models import IPInfoResult


class IPInfoTool(BaseTool):
    """IP 信息分析器：分析 IPv4/IPv6 地址与 CIDR 网络信息。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="network.ip_info",
        name="IP 信息分析器",
        category=ToolCategory.NETWORK,
        icon="network",
        description="分析 IPv4/IPv6 地址及 CIDR 网络信息。",
        version="1.0.0",
        tags=["ip", "cidr", "ipv4", "ipv6"],
        parameters=[
            ToolParameter(
                name="input",
                label="目标地址",
                placeholder="192.168.1.100 或 192.168.1.0/24",
            )
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        value = params.get("input", "")
        raw = value.strip() if isinstance(value, str) else ""
        context.info(f"{self.id} 开始分析：{raw or '(空输入)'}")
        if not raw:
            context.error(f"{self.id} 输入解析失败：输入为空")
            return context.make_result(ResultStatus.FAILED, EMPTY_MESSAGE)
        try:
            info = analyze_ip(raw)
        except ToolInputError as exc:
            context.error(f"{self.id} 输入解析失败：{raw}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        except ValueError:
            context.error(f"{self.id} 输入解析失败：{raw}")
            return context.make_result(ResultStatus.FAILED, UNRECOGNIZED_MESSAGE)
        summary = self._summary(info)
        finding = self._finding(info)
        if finding is not None:
            context.info(f"{self.id} 属性判定：{finding.title}")
        context.info(f"{self.id} 分析完成")
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=[info.model_dump(mode="json", by_alias=True)],
            findings=[finding] if finding is not None else [],
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": info.display_spec(),
            },
        )

    @staticmethod
    def _summary(info: IPInfoResult) -> str:
        version = info.version
        if info.unspecified:
            return f"{version} 未指定地址（{info.address}）"
        if info.loopback:
            return f"{version} 回环地址（{info.address}）"
        if info.multicast:
            return f"{version} 组播地址（{info.address}）"
        if info.link_local:
            return f"{version} 链路本地地址（{info.address}）"
        if info.reserved:
            return f"{version} 受限广播/保留地址（{info.address}）"
        if info.private:
            return f"{version} 私有/特殊用途地址，属于 {info.network} 网络"
        if info.global_:
            return f"{version} 公网地址，属于 {info.network} 网络"
        return f"{version} 地址，属于 {info.network} 网络"

    @staticmethod
    def _finding(info: IPInfoResult) -> Finding | None:
        """One calibrated INFO/FACT finding for the most notable attribute."""
        if info.unspecified:
            title, description = "未指定地址", "该地址为未指定地址，不代表具体主机。"
        elif info.loopback:
            title = "回环地址"
            description = "该地址为回环地址，仅用于本机内部通信。"
        elif info.multicast:
            title = "组播地址"
            description = "该地址属于组播地址范围，用于一对多通信。"
        elif info.link_local:
            title = "链路本地地址"
            description = "该地址为链路本地地址，仅在本地链路上有效。"
        elif info.reserved:
            title = "保留/受限广播地址"
            description = "该地址属于保留或受限广播范围，不能作为普通主机地址使用。"
        elif info.private:
            title = "私有/特殊用途地址"
            description = (
                "该地址不属于公网单播范围，属于私有或特殊用途地址空间"
                "（如 RFC1918、ULA 或文档保留段）。"
            )
        elif info.global_:
            title = "公网地址"
            description = "该地址为全局单播地址。"
        else:
            return None
        return Finding(
            title=title,
            severity=Severity.INFO,
            kind=FindingKind.FACT,
            description=description,
            evidence=f"network={info.network}",
            source="network.ip_info",
        )
