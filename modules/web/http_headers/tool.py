"""HttpHeadersTool: fetch and display response headers (HEAD with GET fallback)."""

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
    ToolParameterKind,
    ToolParameters,
)
from infrastructure.network import HttpClient, HttpResponse, host_scope_note, redact_header_value
from modules.web.cookie_analysis.cookies import mask_set_cookie

DISPLAY_SPEC: dict[str, Any] = {
    "title": "HTTP Header",
    "table": {
        "columns": [
            {"field": "header", "label": "Header"},
            {"field": "value", "label": "Value"},
        ]
    },
}


class HttpHeadersTool(BaseTool):
    """HTTP Header 分析器：HEAD 请求（必要时回退 GET）并展示响应头。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="web.http_headers",
        name="HTTP Header 分析器",
        category=ToolCategory.WEB,
        icon="web",
        description="发起 HEAD 请求展示响应头；服务器不支持时安全回退 GET 并记录。",
        parameters=[
            ToolParameter(name="url", label="URL", placeholder="https://example.com"),
            ToolParameter(
                name="method",
                label="方法",
                kind=ToolParameterKind.CHOICE,
                default="HEAD",
                choices=["HEAD", "GET"],
            ),
        ],
    )

    def __init__(self, client: HttpClient | None = None) -> None:
        self._client = client or HttpClient()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw = str(params.get("url", "")).strip()
        method = str(params.get("method", "HEAD")).upper()
        if method not in ("HEAD", "GET"):
            method = "HEAD"
        fallback = False
        try:
            response = self._client.request(
                raw,
                method=method,
                is_cancelled=lambda: context.is_cancelled,
            )
            if method == "HEAD" and 400 <= response.status_code < 600:
                context.info(f"{self.id} HEAD 返回 {response.status_code}，回退 GET")
                fallback = True
                response = self._client.request(
                    raw,
                    method="GET",
                    is_cancelled=lambda: context.is_cancelled,
                )
        except (NetworkError, ToolInputError) as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        rows = self._header_rows(response)
        findings: list[Finding] = []
        if response.redirects:
            chain = " → ".join(f"{hop.status_code} {hop.url}" for hop in response.redirects)
            findings.append(
                Finding(
                    title="发生重定向",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=f"请求经过 {len(response.redirects)} 次重定向：{chain}。",
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
        summary = (
            f"{response.http_version} {response.status_code} · 方法 {response.method}"
            + ("（HEAD 回退 GET）" if fallback else "")
            + f" · 重定向 {len(response.redirects)}"
        )
        context.info(
            f"{self.id} 完成：{response.status_code}，方法 {response.method}，"
            f"重定向 {len(response.redirects)}"
        )
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

    @staticmethod
    def _header_rows(response: HttpResponse) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = [
            {"header": "Status-Code", "value": str(response.status_code)},
            {"header": "HTTP-Version", "value": response.http_version},
            {"header": "Request-URL", "value": response.request_url},
            {"header": "Final-URL", "value": response.final_url},
        ]
        for name, value in response.headers:
            if name.lower() == "set-cookie":
                display = mask_set_cookie(value)
            else:
                display = redact_header_value(name, value)
            rows.append({"header": name, "value": display})
        return rows
