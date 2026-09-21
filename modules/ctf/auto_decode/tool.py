"""AutoDecodeTool: heuristic multi-encoding candidate detection."""

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
from modules.ctf.auto_decode.decoders import decode_candidates

DISPLAY_SPEC: dict[str, Any] = {
    "title": "Auto Decode 候选",
    "table": {
        "columns": [
            {"field": "encoding", "label": "候选编码"},
            {"field": "confidence", "label": "置信度"},
            {"field": "decoded", "label": "解码结果"},
            {"field": "description", "label": "说明"},
            {"field": "chain", "label": "解码链"},
            {"field": "depth", "label": "层数"},
        ]
    },
}

MAX_DECODED_LENGTH = 1000


class AutoDecodeTool(BaseTool):
    """Auto Decode：启发式识别 Base64/Hex/URL/ROT/JWT 等候选编码。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="ctf.auto_decode",
        name="Auto Decode",
        category=ToolCategory.CTF,
        icon="ctf",
        description=(
            "对未知文本尝试 Base64/Base32/Base58/Hex/Binary/URL/Unicode/ROT/JWT 解码，"
            "按置信度给出候选。结果仅为启发式参考，不是确定性结论。"
        ),
        parameters=[
            ToolParameter(
                name="input",
                label="未知文本",
                kind=ToolParameterKind.MULTILINE,
                placeholder="SGVsbG8= 或 68656c6c6f",
            ),
            ToolParameter(
                name="max_depth",
                label="最大递归层数",
                kind=ToolParameterKind.INTEGER,
                default=5,
                minimum=1,
                maximum=10,
            ),
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        text = str(params.get("input", ""))
        if not text.strip():
            message = "请输入要分析的文本。"
            context.error(f"{self.id} {message}")
            return context.make_result(ResultStatus.FAILED, message)
        context.info(f"{self.id} 开始分析：输入 {len(text)} 字符")
        candidates = decode_candidates(text, max_depth=int(params.get("max_depth", 5)))
        rows = [
            {
                "encoding": candidate.name,
                "confidence": candidate.level,
                "decoded": (
                    candidate.decoded
                    if len(candidate.decoded) <= MAX_DECODED_LENGTH
                    else candidate.decoded[:MAX_DECODED_LENGTH] + "…"
                ),
                "description": candidate.description,
                "chain": " → ".join(candidate.chain),
                "depth": candidate.depth,
            }
            for candidate in candidates
        ]
        if candidates:
            summary = (
                f"发现 {len(candidates)} 个候选编码，最高置信 {candidates[0].name}"
                f"（{candidates[0].level}）。结果仅为启发式参考。"
            )
        else:
            summary = "未发现高置信候选编码。结果仅为启发式参考。"
        context.info(f"{self.id} 完成：{len(candidates)} 个候选")
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=rows,
            findings=[
                Finding(
                    title="候选编码为启发式识别",
                    severity=Severity.INFO,
                    kind=FindingKind.HEURISTIC,
                    description=(
                        "候选结果基于格式特征与可打印字符比例评分，不能作为确定性编码结论。"
                    ),
                    source=self.id,
                )
            ],
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
