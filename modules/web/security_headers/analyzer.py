"""Security header presence analysis (facts, not vulnerability verdicts)."""

from __future__ import annotations

from typing import Any

from core.finding import Finding, FindingKind, Severity
from infrastructure.network import HttpResponse

CHECKED_HEADERS: tuple[tuple[str, str, str], ...] = (
    (
        "Content-Security-Policy",
        "限制可加载的资源来源，缓解注入类风险。",
        "根据站点实际资源加载策略配置 CSP。",
    ),
    (
        "X-Content-Type-Options",
        "禁止浏览器 MIME 嗅探。",
        "建议设置 nosniff。",
    ),
    (
        "X-Frame-Options",
        "限制页面被嵌入 iframe。",
        "根据实际嵌入需求设置 DENY/SAMEORIGIN。",
    ),
    (
        "Strict-Transport-Security",
        "强制浏览器仅通过 HTTPS 访问。",
        "在 HTTPS 站点上启用 HSTS。",
    ),
    (
        "Referrer-Policy",
        "控制跨域请求中的 Referrer 信息。",
        "根据隐私需求配置 Referrer-Policy。",
    ),
    (
        "Permissions-Policy",
        "限制浏览器特性（摄像头、定位等）的使用。",
        "按最小权限原则配置 Permissions-Policy。",
    ),
    (
        "Cross-Origin-Opener-Policy",
        "隔离跨源窗口，缓解跨源信息泄露。",
        "评估后配置 COOP。",
    ),
    (
        "Cross-Origin-Resource-Policy",
        "限制其他源加载本站资源。",
        "评估后配置 CORP。",
    ),
    (
        "Cross-Origin-Embedder-Policy",
        "要求嵌入资源显式声明跨源许可。",
        "评估后配置 COEP。",
    ),
)


def analyze_security_headers(response: HttpResponse) -> list[dict[str, Any]]:
    """Return one row per checked header with presence status."""
    rows: list[dict[str, Any]] = []
    for name, description, recommendation in CHECKED_HEADERS:
        value = response.first_header(name)
        rows.append(
            {
                "header": name,
                "status": "已配置" if value is not None else "未配置",
                "value": value or "-",
                "description": description,
                "recommendation": recommendation,
            }
        )
    return rows


def missing_header_findings(response: HttpResponse, source: str) -> list[Finding]:
    """LOW findings for missing headers; absence is not a vulnerability verdict."""
    findings: list[Finding] = []
    for name, _description, recommendation in CHECKED_HEADERS:
        if response.first_header(name) is None:
            findings.append(
                Finding(
                    title=f"缺少 {name}",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description=f"响应中未检测到 {name}。缺少该头不等于一定存在漏洞。",
                    evidence=f"missing={name}",
                    recommendation=recommendation,
                    source=source,
                )
            )
    return findings
