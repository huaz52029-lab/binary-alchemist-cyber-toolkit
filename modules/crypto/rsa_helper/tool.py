"""RsaHelperTool: offline RSA parameter and public key analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from core.exceptions import DependencyMissingError, ToolInputError
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
from modules.crypto.rsa_helper.rsa import RsaParameters, analyze_parameters, parse_int_field

DISPLAY_SPEC: dict[str, Any] = {
    "title": "RSA 分析结果",
    "sections": [
        {
            "title": "提供参数",
            "items": [
                {"field": "n", "label": "n"},
                {"field": "e", "label": "e"},
                {"field": "d", "label": "d"},
                {"field": "p", "label": "p"},
                {"field": "q", "label": "q"},
            ],
        },
        {
            "title": "关系验证",
            "items": [
                {"field": "has_p", "label": "提供 p"},
                {"field": "has_q", "label": "提供 q"},
                {"field": "n_matches_pq", "label": "n = p × q 验证"},
                {"field": "phi", "label": "φ(n)"},
                {"field": "gcd_e_phi", "label": "gcd(e, φ(n))"},
                {"field": "d_computed", "label": "计算的 d"},
                {"field": "d_verified", "label": "e·d ≡ 1 (mod φ) 验证"},
            ],
        },
        {
            "title": "PEM 公钥",
            "items": [
                {"field": "key_type", "label": "密钥类型"},
                {"field": "key_size", "label": "密钥长度(bits)"},
            ],
        },
    ],
}


class RsaHelperTool(BaseTool):
    """RSA 辅助分析器：参数关系、φ(n)、d 计算与 PEM 公钥解析（离线）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="crypto.rsa_helper",
        name="RSA 辅助",
        category=ToolCategory.CRYPTO,
        icon="crypto",
        description=(
            "分析 RSA 参数（n/e/d/p/q）的数学关系、计算 φ(n) 与 d，或解析 PEM 公钥。"
            "本工具不做网络攻击，也不猜测私钥。"
        ),
        parameters=[
            ToolParameter(
                name="mode",
                label="模式",
                kind=ToolParameterKind.CHOICE,
                default="parameters",
                choices=["parameters", "pem"],
                choice_labels=["参数分析", "PEM 公钥解析"],
            ),
            ToolParameter(name="n", label="n", visible_when={"mode": "parameters"}),
            ToolParameter(name="e", label="e", visible_when={"mode": "parameters"}),
            ToolParameter(name="d", label="d", visible_when={"mode": "parameters"}),
            ToolParameter(name="p", label="p", visible_when={"mode": "parameters"}),
            ToolParameter(name="q", label="q", visible_when={"mode": "parameters"}),
            ToolParameter(
                name="pem_path",
                label="PEM 文件",
                kind=ToolParameterKind.FILE,
                placeholder="选择 PEM 公钥文件",
                visible_when={"mode": "pem"},
            ),
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        mode = str(params.get("mode", "parameters"))
        if mode == "pem":
            return self._analyze_pem(params, context)
        return self._analyze_parameters(params, context)

    def _analyze_parameters(
        self,
        params: ToolParameters,
        context: ExecutionContext,
    ) -> ToolResult:
        try:
            parameters = RsaParameters(
                n=parse_int_field(str(params.get("n", "")), "n"),
                e=parse_int_field(str(params.get("e", "")), "e"),
                d=parse_int_field(str(params.get("d", "")), "d"),
                p=parse_int_field(str(params.get("p", "")), "p"),
                q=parse_int_field(str(params.get("q", "")), "q"),
            )
        except ToolInputError as exc:
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        if parameters.n is None and (parameters.p is None or parameters.q is None):
            message = "请至少提供 n，或同时提供 p 与 q。"
            context.error(f"{self.id} {message}")
            return context.make_result(ResultStatus.FAILED, message)
        context.info(
            f"{self.id} 参数分析：n={len(str(parameters.n or ''))}位，"
            f"e={len(str(parameters.e or ''))}位，"
            f"p={'有' if parameters.p is not None else '无'}，"
            f"q={'有' if parameters.q is not None else '无'}"
        )
        analysis = analyze_parameters(parameters)
        findings: list[Finding] = []
        if analysis["n_matches_pq"] is True:
            findings.append(
                Finding(
                    title="n = p × q 验证通过",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description="提供的 n 与 p×q 一致。",
                    source=self.id,
                )
            )
        elif analysis["n_matches_pq"] is False:
            findings.append(
                Finding(
                    title="n 与 p×q 不一致",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description="提供的 n 与 p×q 不一致，参数可能存在错误。",
                    source=self.id,
                )
            )
        if analysis["gcd_e_phi"] == 1:
            findings.append(
                Finding(
                    title="e 与 φ(n) 互质",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description="gcd(e, φ(n)) = 1，满足 RSA 公钥指数条件，可计算私钥指数 d。",
                    source=self.id,
                )
            )
        if analysis["d_verified"] is True:
            findings.append(
                Finding(
                    title="d 与 e 互为模逆",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description="验证 e·d ≡ 1 (mod φ(n)) 成立。",
                    source=self.id,
                )
            )
        row: dict[str, Any] = {
            "n": str(parameters.n) if parameters.n is not None else None,
            "e": str(parameters.e) if parameters.e is not None else None,
            "d": str(parameters.d) if parameters.d is not None else None,
            "p": str(parameters.p) if parameters.p is not None else None,
            "q": str(parameters.q) if parameters.q is not None else None,
            "has_p": "是" if analysis["has_p"] else "否",
            "has_q": "是" if analysis["has_q"] else "否",
            "n_matches_pq": analysis["n_matches_pq"],
            "phi": analysis["phi"],
            "gcd_e_phi": analysis["gcd_e_phi"],
            "d_computed": analysis["d_computed"],
            "d_verified": analysis["d_verified"],
        }
        context.info(
            f"{self.id} 完成：d可计算={'d_computed' in row and row['d_computed'] is not None}"
        )
        return context.make_result(
            ResultStatus.SUCCESS,
            "RSA 参数分析完成。",
            data=[row],
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )

    def _analyze_pem(
        self,
        params: ToolParameters,
        context: ExecutionContext,
    ) -> ToolResult:
        raw_path = str(params.get("pem_path", "")).strip()
        if not raw_path:
            return context.make_result(ResultStatus.FAILED, "请选择 PEM 公钥文件。")
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            return context.make_result(ResultStatus.FAILED, "PEM 文件不存在。")
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise DependencyMissingError(
                "cryptography is not installed",
                user_message="缺少 cryptography 依赖，请安装：pip install -e '.[crypto]'",
            ) from exc
        try:
            key = serialization.load_pem_public_key(path.read_bytes())
        except (ValueError, TypeError) as exc:
            context.error(f"{self.id} PEM 解析失败：{exc}")
            return context.make_result(ResultStatus.FAILED, "无法解析PEM公钥文件。")
        if not isinstance(key, rsa.RSAPublicKey):
            context.error(f"{self.id} 公钥不是 RSA 类型")
            return context.make_result(ResultStatus.FAILED, "公钥不是 RSA 类型。")
        numbers = key.public_numbers()
        context.info(f"{self.id} PEM 解析完成：{key.key_size} bits")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"PEM RSA 公钥解析完成（{key.key_size} bits）。",
            data=[
                {
                    "key_type": "RSA 公钥",
                    "key_size": key.key_size,
                    "n": str(numbers.n),
                    "e": str(numbers.e),
                }
            ],
            findings=[
                Finding(
                    title="PEM 公钥解析成功",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=f"解析到 {key.key_size} 位 RSA 公钥（n 与 e）。",
                    source=self.id,
                )
            ],
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
