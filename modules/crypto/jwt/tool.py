"""JwtTool: offline JWT structure decoder and claim analyzer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from core.exceptions import ToolInputError
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
from modules.crypto.jwt.parser import parse_jwt

DISPLAY_SPEC: dict[str, Any] = {
    "title": "JWT 解析结果",
    "sections": [
        {
            "title": "基本信息",
            "items": [
                {"field": "algorithm", "label": "算法(alg)"},
                {"field": "type", "label": "类型(typ)"},
                {
                    "field": "signature_present",
                    "label": "签名存在",
                },
                {"field": "signature_length", "label": "签名长度"},
            ],
        },
        {
            "title": "时间声明",
            "items": [
                {"field": "issued_at", "label": "签发时间(iat)"},
                {"field": "expires_at", "label": "过期时间(exp)"},
                {"field": "not_before", "label": "生效时间(nbf)"},
            ],
        },
        {
            "title": "主体",
            "items": [
                {"field": "issuer", "label": "签发者(iss)"},
                {"field": "subject", "label": "主体(sub)"},
            ],
        },
        {
            "title": "原始数据",
            "items": [
                {"field": "header_json", "label": "Header"},
                {"field": "payload_json", "label": "Payload"},
            ],
        },
    ],
}


def _timestamp(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return ""
    try:
        return datetime.fromtimestamp(float(value), UTC).isoformat()
    except (OverflowError, OSError, ValueError):
        return str(value)


class JwtTool(BaseTool):
    """JWT 解析器：解码 Header/Payload、分析声明与签名存在性（离线）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="crypto.jwt",
        name="JWT 解析器",
        category=ToolCategory.CRYPTO,
        icon="crypto",
        description=(
            "离线解析 JWT 的 Header/Payload、分析 alg/typ/exp/iat/nbf/iss/sub 声明与签名。"
            "本工具不猜测密钥、不做在线攻击。"
        ),
        parameters=[
            ToolParameter(
                name="token",
                label="JWT Token",
                kind=ToolParameterKind.MULTILINE,
                placeholder="xxxxx.yyyyy.zzzzz",
            )
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        token = str(params.get("token", "")).strip()
        context.info(f"{self.id} 开始解析：{len(token)} 字符")
        try:
            data = parse_jwt(token)
        except ToolInputError as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        header = data.header
        payload = data.payload
        findings: list[Finding] = []
        algorithm = header.get("alg")
        if algorithm is None:
            findings.append(
                Finding(
                    title="未发现 alg 字段",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description="Header 中缺少 alg 声明，无法确定签名算法。",
                    source=self.id,
                )
            )
        else:
            findings.append(
                Finding(
                    title="签名算法",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=f"Header 声明的算法为 {algorithm}。",
                    evidence=f"alg={algorithm}",
                    source=self.id,
                )
            )
        now = datetime.now(UTC).timestamp()
        if "exp" not in payload:
            findings.append(
                Finding(
                    title="未发现 exp 字段",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description="未发现 exp 声明，Token 可能长期有效。",
                    source=self.id,
                )
            )
        elif isinstance(payload["exp"], (int, float)) and not isinstance(payload["exp"], bool):
            if payload["exp"] < now:
                findings.append(
                    Finding(
                        title="Token 已过期",
                        severity=Severity.LOW,
                        kind=FindingKind.FACT,
                        description="exp 声明早于当前时间，Token 可能已经过期。",
                        evidence=f"exp={_timestamp(payload['exp'])}",
                        source=self.id,
                    )
                )
            else:
                findings.append(
                    Finding(
                        title="exp 未过期",
                        severity=Severity.INFO,
                        kind=FindingKind.FACT,
                        description="exp 声明晚于当前时间，Token 尚未过期。",
                        source=self.id,
                    )
                )
        if isinstance(payload.get("nbf"), (int, float)) and payload["nbf"] > now:
            findings.append(
                Finding(
                    title="Token 尚未生效",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description="nbf 声明晚于当前时间，Token 尚未生效。",
                    evidence=f"nbf={_timestamp(payload['nbf'])}",
                    source=self.id,
                )
            )
        if data.signature:
            findings.append(
                Finding(
                    title="签名存在",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description="Token 包含非空签名段。",
                    evidence=f"signature_length={len(data.signature)}",
                    source=self.id,
                )
            )
        else:
            findings.append(
                Finding(
                    title="没有签名内容",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description="签名段为空（可能为 alg=none 或输入被截断）。",
                    source=self.id,
                )
            )
        row: dict[str, Any] = {
            "algorithm": str(algorithm) if algorithm is not None else None,
            "type": str(header.get("typ")) if header.get("typ") is not None else None,
            "signature_present": "是" if data.signature else "否",
            "signature_length": len(data.signature),
            "issued_at": _timestamp(payload.get("iat")),
            "expires_at": _timestamp(payload.get("exp")),
            "not_before": _timestamp(payload.get("nbf")),
            "issuer": str(payload["iss"]) if payload.get("iss") is not None else None,
            "subject": str(payload["sub"]) if payload.get("sub") is not None else None,
            "header_json": data.header_json,
            "payload_json": data.payload_json,
        }
        context.info(
            f"{self.id} 完成：alg={algorithm}，exp={'有' if 'exp' in payload else '无'}，"
            f"签名长度 {len(data.signature)}"
        )
        summary = (
            f"JWT 解析完成：Header 声明 alg={algorithm or '无'}，"
            f"签名{'存在' if data.signature else '为空'}。"
        )
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=[row],
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
