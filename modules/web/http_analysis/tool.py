"""HttpAnalysisTool: composite HTTP request analysis."""

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
from infrastructure.network import (
    HttpClient,
    HttpResponse,
    TlsClient,
    host_scope_note,
    redact_header_value,
)
from modules.web.cookie_analysis.cookies import parse_set_cookie
from modules.web.cookie_analysis.tool import cookie_findings, cookie_rows
from modules.web.http_analysis.meta import parse_page_metadata
from modules.web.security_headers.analyzer import analyze_security_headers, missing_header_findings
from modules.web.tls_info.tool import tls_findings

DISPLAY_SPEC: dict[str, Any] = {
    "title": "HTTP 请求分析",
    "table": {
        "columns": [
            {"field": "section", "label": "分类"},
            {"field": "item", "label": "项目"},
            {"field": "value", "label": "值"},
        ]
    },
}


class HttpAnalysisTool(BaseTool):
    """HTTP 请求分析：请求/响应、重定向、安全头、Cookie、TLS 与页面元信息。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="web.http_analysis",
        name="HTTP 请求分析",
        category=ToolCategory.WEB,
        icon="web",
        description="一次 GET 请求汇总状态、Header、重定向链、安全头、Cookie、TLS 与页面元信息。",
        parameters=[ToolParameter(name="url", label="URL", placeholder="https://example.com")],
    )

    def __init__(
        self,
        client: HttpClient | None = None,
        tls_client: TlsClient | None = None,
    ) -> None:
        self._client = client or HttpClient()
        self._tls_client = tls_client or TlsClient()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw = str(params.get("url", "")).strip()
        try:
            response = self._client.request(raw, is_cancelled=lambda: context.is_cancelled)
        except (NetworkError, ToolInputError) as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        rows = self._build_rows(response)
        findings = missing_header_findings(response, self.id)
        cookies = [parse_set_cookie(header) for header in response.header_values("set-cookie")]
        findings.extend(cookie_findings(cookies, self.id))
        if response.redirects:
            chain = " → ".join(
                f"{hop.status_code} {hop.location or hop.url}" for hop in response.redirects
            )
            findings.append(
                Finding(
                    title="发生重定向",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=f"请求经过 {len(response.redirects)} 次重定向。",
                    evidence=chain,
                    source=self.id,
                )
            )
        if response.body_truncated:
            findings.append(
                Finding(
                    title="响应体已截断",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description="响应体超过显示上限，已截断。",
                    source=self.id,
                )
            )
        scheme = urlsplit(response.final_url).scheme
        if scheme == "https":
            host = urlsplit(response.final_url).hostname
            if host is not None:
                try:
                    tls_info = self._tls_client.get_tls_info(
                        host, urlsplit(response.final_url).port or 443
                    )
                    findings.extend(tls_findings(tls_info, self.id))
                    rows.append({"section": "TLS", "item": "版本", "value": tls_info.version})
                    rows.append({"section": "TLS", "item": "证书主题", "value": tls_info.subject})
                except NetworkError as exc:
                    rows.append({"section": "TLS", "item": "分析失败", "value": exc.user_message})
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
            f"GET {response.final_url} → {response.status_code}"
            f"（{response.elapsed_seconds:.2f}s，重定向 {len(response.redirects)}）"
        )
        context.info(
            f"{self.id} 完成：{response.status_code}，耗时 {response.elapsed_seconds:.2f}s"
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

    def _build_rows(self, response: HttpResponse) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = [
            {"section": "请求", "item": "Method", "value": response.method},
            {"section": "请求", "item": "URL", "value": response.request_url},
            {"section": "请求", "item": "User-Agent", "value": "BinaryAlchemist-CyberToolkit"},
            {"section": "响应", "item": "Status", "value": str(response.status_code)},
            {"section": "响应", "item": "Final URL", "value": response.final_url},
            {"section": "响应", "item": "HTTP Version", "value": response.http_version},
            {"section": "响应", "item": "Size", "value": f"{len(response.body or b'')} 字节"},
            {"section": "响应", "item": "耗时", "value": f"{response.elapsed_seconds:.3f}s"},
        ]
        for hop in response.redirects:
            rows.append(
                {
                    "section": "重定向",
                    "item": str(hop.status_code),
                    "value": f"{hop.url} → {hop.location or ''}",
                }
            )
        for name, value in response.headers:
            if name.lower() == "set-cookie":
                continue  # shown structurally via cookies
            rows.append(
                {
                    "section": "Header",
                    "item": name,
                    "value": redact_header_value(name, value),
                }
            )
        cookies = [parse_set_cookie(header) for header in response.header_values("set-cookie")]
        for cookie in cookie_rows(cookies):
            rows.append(
                {
                    "section": "Cookie",
                    "item": cookie["name"],
                    "value": (
                        f"Secure={cookie['secure']} HttpOnly={cookie['http_only']} "
                        f"SameSite={cookie['same_site']} Value={cookie['value_masked']}"
                    ),
                }
            )
        security = analyze_security_headers(response)
        configured = sum(row["status"] == "已配置" for row in security)
        rows.append(
            {
                "section": "安全Header",
                "item": "已配置",
                "value": f"{configured}/{len(security)}",
            }
        )
        content_type = response.first_header("content-type") or ""
        if "html" in content_type and response.body:
            try:
                metadata = parse_page_metadata(response.body.decode("utf-8", errors="replace"))
            except Exception:  # defensive: metadata must never break the analysis
                metadata = None
            if metadata is not None:
                rows.extend(
                    [
                        {"section": "页面", "item": "Title", "value": metadata.title or "-"},
                        {
                            "section": "页面",
                            "item": "Description",
                            "value": metadata.description or "-",
                        },
                        {
                            "section": "页面",
                            "item": "Canonical",
                            "value": metadata.canonical or "-",
                        },
                        {"section": "页面", "item": "Robots", "value": metadata.robots or "-"},
                        {
                            "section": "页面",
                            "item": "Language",
                            "value": metadata.language or "-",
                        },
                    ]
                )
                for key, value in metadata.open_graph.items():
                    rows.append({"section": "OpenGraph", "item": key, "value": value})
        return rows
