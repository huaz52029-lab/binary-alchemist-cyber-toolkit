"""Shared BaseTool implementation for the two-way encoding tools."""

from __future__ import annotations

from typing import ClassVar

from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext
from core.tool_definition import BaseTool, ToolParameters
from modules.encoding.codecs import CODECS

OPERATION_LABELS = {"encode": "编码", "decode": "解码", "transform": "转换"}


class EncodingTool(BaseTool):
    """Generic encode/decode tool driven by a codec registered in ``CODECS``."""

    codec_name: ClassVar[str] = ""

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw = params.get("input", "")
        text = raw if isinstance(raw, str) else ""
        operation = str(params.get("operation", "encode"))
        codec = CODECS[self.codec_name]
        context.info(
            f"{self.id} {OPERATION_LABELS.get(operation, operation)}："
            f"输入 {len(text)} 字符（{codec.name}）"
        )
        try:
            output = (
                codec.encode(text) if operation in ("encode", "transform") else codec.decode(text)
            )
        except ValueError as exc:
            context.error(f"{self.id} 失败：{exc}")
            return context.make_result(ResultStatus.FAILED, str(exc))
        label = OPERATION_LABELS.get(operation, operation)
        context.info(f"{self.id} 完成：输出 {len(output)} 字符")
        summary = (
            f"{self.definition.name} {label}完成（输入 {len(text)} 字符 → 输出 {len(output)} 字符）"
        )
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=[{"operation": label, "input": text, "output": output}],
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": {
                    "title": f"{self.definition.name} 结果",
                    "sections": [
                        {
                            "title": "结果",
                            "items": [
                                {"field": "operation", "label": "操作"},
                                {"field": "output", "label": "输出"},
                                {"field": "input", "label": "输入"},
                            ],
                        }
                    ],
                },
            },
        )
