"""XorTool: single-byte, repeating-key and hex XOR helpers."""

from __future__ import annotations

from typing import Any, ClassVar

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
from modules.crypto.xor.xor import (
    brute_force_candidates,
    hex_to_bytes,
    preview,
    xor_equal,
    xor_repeating,
    xor_single,
)

BRUTE_DISPLAY_SPEC: dict[str, Any] = {
    "title": "单字节 XOR 候选（按评分排序）",
    "table": {
        "columns": [
            {"field": "key_hex", "label": "密钥"},
            {"field": "score", "label": "评分"},
            {"field": "preview", "label": "候选预览"},
            {"field": "output_hex", "label": "输出(Hex)"},
        ]
    },
}


RESULT_DISPLAY_SPEC: dict[str, Any] = {
    "title": "XOR 结果",
    "sections": [
        {
            "title": "结果",
            "items": [
                {"field": "mode", "label": "模式"},
                {"field": "output_hex", "label": "输出(Hex)"},
                {"field": "preview", "label": "预览"},
            ],
        }
    ],
}


class XorTool(BaseTool):
    """XOR 工具：单字节、单字节遍历评分、重复密钥与 Hex XOR（CTF/学习）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="crypto.xor",
        name="XOR 工具",
        category=ToolCategory.CRYPTO,
        icon="crypto",
        description="单字节 XOR、单字节自动遍历评分、重复密钥 XOR 与等长 Hex XOR。",
        parameters=[
            ToolParameter(
                name="mode",
                label="模式",
                kind=ToolParameterKind.CHOICE,
                default="single",
                choices=["single", "brute", "repeating", "hex_xor"],
                choice_labels=["单字节XOR", "单字节自动遍历", "重复密钥XOR", "Hex XOR"],
            ),
            ToolParameter(
                name="input",
                label="输入(Hex)",
                kind=ToolParameterKind.MULTILINE,
                placeholder="48656c6c6f",
            ),
            ToolParameter(
                name="input_b",
                label="输入B(Hex)",
                kind=ToolParameterKind.MULTILINE,
                placeholder="0102030405",
                visible_when={"mode": "hex_xor"},
            ),
            ToolParameter(
                name="key_byte",
                label="密钥(0-255)",
                kind=ToolParameterKind.INTEGER,
                default=32,
                minimum=0,
                maximum=255,
                visible_when={"mode": "single"},
            ),
            ToolParameter(
                name="key",
                label="密钥(UTF-8)",
                placeholder="key",
                visible_when={"mode": "repeating"},
            ),
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        mode = str(params.get("mode", "single"))
        context.info(f"{self.id} 启动：模式={mode}")
        raw = str(params.get("input", ""))
        try:
            if mode == "brute":
                data = hex_to_bytes(raw)
                if not data:
                    return context.make_result(ResultStatus.FAILED, "输入不能为空。")
                rows = brute_force_candidates(data, is_cancelled=lambda: context.is_cancelled)
                best = rows[0]
                summary = (
                    f"已尝试 256 个密钥，最高分 {best['score']}（key {best['key_hex']}）。"
                    "评分仅为启发式参考。"
                )
                return context.make_result(
                    ResultStatus.SUCCESS,
                    summary,
                    data=rows,
                    findings=[
                        Finding(
                            title="评分为启发式参考",
                            severity=Severity.INFO,
                            kind=FindingKind.HEURISTIC,
                            description="候选评分基于可打印字符比例，不能据此断定某个结果就是明文。",
                            evidence="score_basis=printable_and_letter_ratio",
                            source=self.id,
                        )
                    ],
                    metadata={
                        "tool_id": self.id,
                        "tool_version": self.definition.version,
                        "display": BRUTE_DISPLAY_SPEC,
                    },
                )
            if mode == "hex_xor":
                data = hex_to_bytes(raw)
                other = hex_to_bytes(str(params.get("input_b", "")))
                output = xor_equal(data, other)
                label = "Hex XOR"
            elif mode == "repeating":
                data = hex_to_bytes(raw)
                key = str(params.get("key", "")).encode("utf-8")
                output = xor_repeating(data, key)
                label = "重复密钥 XOR"
            else:
                data = hex_to_bytes(raw)
                key_byte = int(params.get("key_byte", 0))
                if not 0 <= key_byte <= 255:
                    return context.make_result(ResultStatus.FAILED, "密钥必须在 0-255 之间。")
                output = xor_single(data, key_byte)
                label = "单字节 XOR"
        except ValueError as exc:
            context.error(f"{self.id} 失败：{exc}")
            return context.make_result(ResultStatus.FAILED, str(exc))
        context.info(f"{self.id} 完成：输出 {len(output)} 字节")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"{label} 完成（输出 {len(output)} 字节）",
            data=[
                {
                    "mode": label,
                    "output_hex": output.hex(),
                    "preview": preview(output),
                }
            ],
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": RESULT_DISPLAY_SPEC,
            },
        )
