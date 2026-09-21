"""CookieAnalysisTool: analyze Set-Cookie security attributes."""

from __future__ import annotations

from typing import Any, ClassVar

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
from modules.web.cookie_analysis.cookies import CookieInfo, parse_set_cookie

DISPLAY_SPEC: dict[str, Any] = {
    "title": "Cookie 分析结果",
    "table": {
        "columns": [
            {"field": "name", "label": "Name"},
            {"field": "secure", "label": "Secure"},
            {"field": "http_only", "label": "HttpOnly"},
            {"field": "same_site", "label": "SameSite"},
            {"field": "domain", "label": "Domain"},
            {"field": "path", "label": "Path"},
            {"field": "max_age", "label": "Max-Age"},
            {"field": "expires", "label": "Expires"},
            {"field": "value_masked", "label": "Value(脱敏)"},
        ]
    },
}


def cookie_findings(cookies: list[CookieInfo], source: str) -> list[Finding]:
    """Fact-based attribute findings, never vulnerability verdicts."""
    findings: list[Finding] = []
    for cookie in cookies:
        if not cookie.secure:
            findings.append(
                Finding(
                    title=f"Cookie「{cookie.name}」未设置 Secure",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description=(
                        "该 Cookie 未声明 Secure 属性；在 HTTPS 站点下应设置"
                        "以限制仅经加密连接传输。"
                    ),
                    evidence=f"cookie={cookie.name}",
                    source=source,
                )
            )
        if not cookie.http_only:
            findings.append(
                Finding(
                    title=f"Cookie「{cookie.name}」未设置 HttpOnly",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description="该 Cookie 未启用 HttpOnly，脚本可能通过 document.cookie 读取。",
                    evidence=f"cookie={cookie.name}",
                    source=source,
                )
            )
        if cookie.same_site is None:
            findings.append(
                Finding(
                    title=f"Cookie「{cookie.name}」未设置 SameSite",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description="该 Cookie 未明确设置 SameSite 属性。",
                    evidence=f"cookie={cookie.name}",
                    source=source,
                )
            )
    return findings


def cookie_rows(cookies: list[CookieInfo]) -> list[dict[str, Any]]:
    return [
        {
            "name": cookie.name,
            "secure": "是" if cookie.secure else "否",
            "http_only": "是" if cookie.http_only else "否",
            "same_site": cookie.same_site or "-",
            "domain": cookie.domain or "-",
            "path": cookie.path or "-",
            "max_age": cookie.max_age or "-",
            "expires": cookie.expires or "-",
            "value_masked": cookie.value_masked,
        }
        for cookie in cookies
    ]


class CookieAnalysisTool(BaseTool):
    """Cookie 安全分析：解析 Set-Cookie 的 Secure/HttpOnly/SameSite 等属性。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="web.cookie_analysis",
        name="Cookie 安全分析",
        category=ToolCategory.WEB,
        icon="web",
        description="分析响应 Set-Cookie 的安全属性（值默认脱敏，不写入日志）。",
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
        cookies = [parse_set_cookie(header) for header in response.header_values("set-cookie")]
        for cookie in cookies:
            context.info(
                f"{self.id} Cookie：name={cookie.name}，secure={cookie.secure}，"
                f"httponly={cookie.http_only}"
            )
        findings = cookie_findings(cookies, self.id)
        from urllib.parse import urlsplit

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
        summary = "响应中没有 Set-Cookie。" if not cookies else f"共分析 {len(cookies)} 个 Cookie。"
        context.info(f"{self.id} 完成：{len(cookies)} 个 Cookie")
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=cookie_rows(cookies),
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
