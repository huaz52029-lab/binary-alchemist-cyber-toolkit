"""TlsInfoTool: negotiated TLS parameters and certificate inspection."""

from __future__ import annotations

from datetime import UTC, datetime
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
from infrastructure.network import TlsClient, TlsInfo, normalize_web_url

DISPLAY_SPEC: dict[str, Any] = {
    "title": "TLS 信息",
    "sections": [
        {
            "title": "连接",
            "items": [
                {"field": "host", "label": "主机"},
                {"field": "port", "label": "端口"},
                {"field": "version", "label": "TLS 版本"},
                {"field": "cipher_name", "label": "密码套件"},
            ],
        },
        {
            "title": "证书",
            "items": [
                {"field": "subject", "label": "主题"},
                {"field": "issuer", "label": "签发者"},
                {"field": "not_before", "label": "生效时间"},
                {"field": "not_after", "label": "过期时间"},
                {"field": "serial_number", "label": "序列号"},
                {"field": "sha256_fingerprint", "label": "SHA-256 指纹"},
                {"field": "san_dns", "label": "SAN(DNS)"},
            ],
        },
        {
            "title": "验证",
            "items": [
                {"field": "self_signed", "label": "自签名"},
                {"field": "hostname_match", "label": "主机名匹配"},
                {"field": "chain_subjects", "label": "证书链"},
            ],
        },
    ],
}


def _cert_expiry(not_after: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(not_after)
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def tls_findings(info: TlsInfo, source: str) -> list[Finding]:
    findings: list[Finding] = []
    expires = _cert_expiry(info.not_after)
    now = datetime.now(UTC)
    if expires is not None:
        if expires < now:
            findings.append(
                Finding(
                    title="证书已过期",
                    severity=Severity.HIGH,
                    kind=FindingKind.FACT,
                    description="证书的 Not After 早于当前时间，证书已过期。",
                    evidence=f"not_after={info.not_after}",
                    source=source,
                )
            )
        elif (expires - now).days < 30:
            findings.append(
                Finding(
                    title="证书即将过期",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description="距离证书过期时间较短（少于 30 天），请及时续期。",
                    evidence=f"not_after={info.not_after}",
                    source=source,
                )
            )
    if info.self_signed:
        findings.append(
            Finding(
                title="自签名证书",
                severity=Severity.INFO,
                kind=FindingKind.FACT,
                description="该证书为自签名；内部系统、开发或实验环境可能合理使用自签名证书。",
                source=source,
            )
        )
    if info.version in ("TLSv1", "TLSv1.1"):
        findings.append(
            Finding(
                title="协议版本较旧",
                severity=Severity.LOW,
                kind=FindingKind.FACT,
                description=f"协商版本为 {info.version}，协议较旧，应根据实际兼容性需求评估。",
                evidence=f"version={info.version}",
                source=source,
            )
        )
    if not info.hostname_match:
        findings.append(
            Finding(
                title="证书与主机名不匹配",
                severity=Severity.HIGH,
                kind=FindingKind.FACT,
                description="证书的 SAN/CN 与目标主机名不匹配。",
                evidence="certificate hostname mismatch",
                source=source,
            )
        )
    return findings


class TlsInfoTool(BaseTool):
    """TLS 信息分析：版本、密码套件、证书与验证状态。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="web.tls_info",
        name="TLS 信息分析",
        category=ToolCategory.WEB,
        icon="web",
        description="获取 HTTPS 连接的 TLS 版本、密码套件与证书信息（不绕过验证）。",
        parameters=[
            ToolParameter(name="url", label="HTTPS URL", placeholder="https://example.com")
        ],
    )

    def __init__(self, client: TlsClient | None = None) -> None:
        self._client = client or TlsClient()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw = str(params.get("url", "")).strip()
        try:
            url, _assumed = normalize_web_url(raw)
        except ToolInputError as exc:
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        split = urlsplit(url)
        if split.scheme != "https":
            message = "TLS分析需要HTTPS URL。"
            context.error(f"{self.id} {message}")
            return context.make_result(ResultStatus.FAILED, message)
        host = split.hostname
        port = split.port or 443
        if host is None:
            return context.make_result(ResultStatus.FAILED, "URL 缺少主机名。")
        context.info(f"{self.id} 开始 TLS 分析：{host}:{port}")
        try:
            info = self._client.get_tls_info(host, port)
        except (NetworkError, ToolInputError) as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        findings = tls_findings(info, self.id)
        row: dict[str, Any] = {
            "host": info.host,
            "port": info.port,
            "version": info.version,
            "cipher_name": info.cipher_name,
            "subject": info.subject,
            "issuer": info.issuer,
            "not_before": info.not_before,
            "not_after": info.not_after,
            "serial_number": info.serial_number,
            "sha256_fingerprint": info.sha256_fingerprint,
            "san_dns": ", ".join(info.san_dns) or None,
            "self_signed": "是" if info.self_signed else "否",
            "hostname_match": "是" if info.hostname_match else "否",
            "chain_subjects": " → ".join(info.chain_subjects) or None,
        }
        context.info(f"{self.id} 完成：{info.version}，自签名={info.self_signed}")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"TLS 分析完成：{info.version} / {info.cipher_name}。",
            data=[row],
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
