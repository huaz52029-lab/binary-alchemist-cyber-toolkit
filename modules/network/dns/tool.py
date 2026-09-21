"""DnsTool: structured DNS record queries."""

from __future__ import annotations

from typing import ClassVar

from pydantic import ValidationError

from core.exceptions import NetworkError, ToolInputError
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
from infrastructure.network import SUPPORTED_RECORD_TYPES, DnsClient
from modules.network.dns.models import RECORD_TYPE_CHOICES, DnsInput, build_display_spec


class DnsTool(BaseTool):
    """DNS 查询：查询 A/AAAA/CNAME/MX/NS/TXT/PTR/SOA 记录。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="network.dns",
        name="DNS 查询",
        category=ToolCategory.NETWORK,
        icon="dns",
        description="查询域名的 A/AAAA/CNAME/MX/NS/TXT/PTR/SOA 记录。",
        version="1.0.0",
        tags=["dns", "records"],
        parameters=[
            ToolParameter(name="domain", label="域名", placeholder="example.com"),
            ToolParameter(
                name="record_type",
                label="记录类型",
                kind=ToolParameterKind.CHOICE,
                default="A",
                choices=RECORD_TYPE_CHOICES,
            ),
            ToolParameter(
                name="nameserver",
                label="DNS 服务器（可选）",
                placeholder="留空使用系统默认 DNS",
            ),
        ],
    )

    def __init__(self, client: DnsClient | None = None) -> None:
        self._client = client or DnsClient()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        try:
            model = DnsInput.model_validate(dict(params))
        except ValidationError as exc:
            context.error(f"{self.id} 参数校验失败：{exc}")
            return context.make_result(ResultStatus.FAILED, "DNS 查询参数无效。")
        if model.record_type not in SUPPORTED_RECORD_TYPES:
            return context.make_result(ResultStatus.FAILED, "不支持的记录类型。")
        nameserver = model.nameserver.strip() or None
        context.info(
            f"{self.id} 查询 {model.domain}（{model.record_type}，"
            f"服务器：{nameserver or '系统默认'}）"
        )
        try:
            records = self._client.query(model.domain, model.record_type, nameserver)
        except NetworkError as exc:
            context.error(f"{self.id} 查询失败：{exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        except ToolInputError as exc:
            context.error(f"{self.id} 查询失败：{exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        context.info(f"{self.id} 完成：{len(records)} 条记录")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"查询 {model.domain} 的 {model.record_type} 记录：共 {len(records)} 条",
            data=[
                {"name": record.name, "type": record.type, "ttl": record.ttl, **record.fields}
                for record in records
            ],
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": build_display_spec(model.record_type),
            },
        )
