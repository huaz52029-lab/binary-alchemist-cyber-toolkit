"""SecurityHeadersTool: presence check for common security headers."""

from __future__ import annotations

from typing import Any, ClassVar
from urllib.parse import urlsplit

from core.exceptions import NetworkError, ToolInputError
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
from infrastructure.network import HttpClient, host_scope_note
from modules.web.security_headers.analyzer import (
    analyze_security_headers,
    missing_header_findings,
)

DISPLAY_SPEC: dict[str, Any] = {
    "title": "Web 安全 Header 检查",
    "table": {
        "columns": [
            {"field": "header", "label": "Header"},
            {"field": "status", "label": "状态"},
            {"field": "value", "label": "值"},
            {"field": "description", "label": "说明"},
            {"field": "recommendation", "label": "建议"},
        ]
    },
}


class SecurityHeadersTool(BaseTool):
    """Web 安全 Header 检查：检测 9 项常见安全响应头。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="web.security_headers",
        name="Web 安全 Header 检查",
        category=ToolCategory.WEB,
        icon="web",
        description="检查 CSP、X-Frame-Options、HSTS 等 9 项安全响应头并给出谨慎的提示。",
        parameters=[ToolParameter(name="url", label="URL", placeholder="https://example.com")],
    )

    def __init__(self, client: HttpClient | None = None) -> None:
        self._client = client or HttpClient()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw = str(params.get("url", "")).strip()
        try:
            response = self._client.request(raw, is_cancelled=lambda: context.is_cancelled)
        except (NetworkError, ToolInputError) as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        rows = analyze_security_headers(response)
        findings = missing_header_findings(response, self.id)
        scheme = urlsplit(response.final_url).scheme
        if scheme == "http":
            findings.append(
                Finding(
                    title="当前使用 HTTP",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description="当前连接使用明文 HTTP，内容未加密传输。",
                    source=self.id,
                )
            )
        else:
            findings.append(
                Finding(
                    title="使用 HTTPS",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description="当前连接使用 TLS 保护的 HTTPS，但这不代表网站绝对安全。",
                    source=self.id,
                )
            )
        note = host_scope_note(urlsplit(response.final_url).hostname or "")
        if note:
            findings.append(
                Finding(
                    title="本机/私有网络目标",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=note,
                    source=self.id,
                )
            )
        configured = sum(row["status"] == "已配置" for row in rows)
        summary = (
            f"安全 Header：{len(rows)} 项，已配置 {configured}，未配置 {len(rows) - configured}。"
        )
        context.info(f"{self.id} 完成：{configured}/{len(rows)} 已配置")
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
