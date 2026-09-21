"""CryptoHelperTool: unified orchestration entry to existing crypto tools."""

from __future__ import annotations

from typing import Any, ClassVar

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
from core.tool_registry import ToolRegistry

TARGETS = {
    "hash": "crypto.hash",
    "base64": "encoding.base64",
    "hex": "encoding.hex",
    "xor": "crypto.xor",
    "rsa": "crypto.rsa_helper",
}


class CryptoHelperTool(BaseTool):
    """Crypto Helper：统一入口编排 Hash/XOR/RSA/Base64/Hex（复用现有工具，不重复实现）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="ctf.crypto_helper",
        name="Crypto Helper",
        category=ToolCategory.CTF,
        icon="ctf",
        description="统一调用已有 Hash/XOR/RSA/Base64/Hex 工具（编排层，不重复实现）。",
        parameters=[
            ToolParameter(
                name="mode",
                label="工具",
                kind=ToolParameterKind.CHOICE,
                default="hash",
                choices=["hash", "base64", "hex", "xor", "rsa"],
                choice_labels=["Hash", "Base64", "Hex", "XOR", "RSA"],
            ),
            ToolParameter(
                name="input",
                label="输入",
                kind=ToolParameterKind.MULTILINE,
                placeholder="文本或 Hex 输入",
            ),
            ToolParameter(
                name="operation",
                label="操作",
                kind=ToolParameterKind.CHOICE,
                default="encode",
                choices=["encode", "decode"],
                choice_labels=["编码", "解码"],
            ),
            ToolParameter(
                name="algorithm",
                label="Hash 算法",
                kind=ToolParameterKind.CHOICE,
                default="SHA256",
                choices=["MD5", "SHA1", "SHA256", "SHA512"],
            ),
            ToolParameter(
                name="key_byte",
                label="XOR 密钥(0-255)",
                kind=ToolParameterKind.INTEGER,
                default=32,
                minimum=0,
                maximum=255,
            ),
            ToolParameter(name="n", label="RSA n", placeholder="3233"),
            ToolParameter(name="e", label="RSA e", placeholder="17"),
            ToolParameter(name="d", label="RSA d"),
            ToolParameter(name="p", label="RSA p", placeholder="61"),
            ToolParameter(name="q", label="RSA q", placeholder="53"),
        ],
    )

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        mode = str(params.get("mode", "hash"))
        target_id = TARGETS.get(mode)
        if target_id is None:
            return context.make_result(ResultStatus.FAILED, "不支持的工具模式。")
        tool = self._registry.get(target_id)
        if tool is None:
            return context.make_result(ResultStatus.FAILED, "目标工具未注册。")
        context.info(f"{self.id} 转发到 {target_id}")
        forwarded: dict[str, Any] = {}
        if mode == "hash":
            forwarded = {
                "mode": "text",
                "input": str(params.get("input", "")),
                "algorithm": str(params.get("algorithm", "SHA256")),
            }
        elif mode in ("base64", "hex"):
            forwarded = {
                "input": str(params.get("input", "")),
                "operation": str(params.get("operation", "encode")),
            }
        elif mode == "xor":
            forwarded = {
                "mode": "single",
                "input": str(params.get("input", "")),
                "key_byte": int(params.get("key_byte", 32)),
            }
        else:
            forwarded = {
                "mode": "parameters",
                "n": str(params.get("n", "")),
                "e": str(params.get("e", "")),
                "d": str(params.get("d", "")),
                "p": str(params.get("p", "")),
                "q": str(params.get("q", "")),
            }
        result = tool.run(forwarded, context)
        return ToolResult(
            status=result.status,
            summary=f"[{target_id}] {result.summary}",
            data=result.data,
            findings=result.findings,
            logs=result.logs,
            duration=result.duration,
            metadata={
                **result.metadata,
                "forwarded_by": self.id,
            },
        )
