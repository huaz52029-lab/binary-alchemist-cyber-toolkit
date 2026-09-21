"""TextAnalysisTool: statistics, frequency, entropy and encoding notes."""

from __future__ import annotations

from collections import Counter
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
from modules.file_analysis.entropy.analyzer import shannon_entropy

DISPLAY_SPEC: dict[str, Any] = {
    "title": "文本分析",
    "table": {
        "columns": [
            {"field": "section", "label": "分类"},
            {"field": "item", "label": "项目"},
            {"field": "value", "label": "值"},
        ]
    },
}


class TextAnalysisTool(BaseTool):
    """Text Analysis：字符/行/词统计、字符频率、熵与编码提示（复用熵服务）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="ctf.text_analysis",
        name="Text Analysis",
        category=ToolCategory.CTF,
        icon="ctf",
        description="文本统计与字符频率分析；熵复用文件分析模块的 Shannon 熵实现。",
        parameters=[
            ToolParameter(
                name="text",
                label="文本",
                kind=ToolParameterKind.MULTILINE,
                placeholder="输入要分析的文本",
            ),
            ToolParameter(
                name="top_n",
                label="高频字符数",
                kind=ToolParameterKind.INTEGER,
                default=20,
                minimum=10,
                maximum=100,
            ),
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        text = str(params.get("text", ""))
        top_n = int(params.get("top_n", 20))
        context.info(f"{self.id} 开始分析：{len(text)} 字符")
        data = text.encode("utf-8")
        digits = sum(char.isdigit() for char in text)
        special = sum(not char.isalnum() and not char.isspace() for char in text)
        rows: list[dict[str, Any]] = [
            {"section": "统计", "item": "字符数", "value": str(len(text))},
            {"section": "统计", "item": "字节数(UTF-8)", "value": str(len(data))},
            {
                "section": "统计",
                "item": "行数",
                "value": str(text.count("\n") + (1 if text else 0)),
            },
            {"section": "统计", "item": "单词数", "value": str(len(text.split()))},
            {
                "section": "统计",
                "item": "空格数",
                "value": str(sum(char.isspace() for char in text)),
            },
            {"section": "统计", "item": "数字数", "value": str(digits)},
            {"section": "统计", "item": "特殊字符数", "value": str(special)},
        ]
        counts = [0] * 256
        for byte in data:
            counts[byte] += 1
        entropy = round(shannon_entropy(counts, len(data)), 4)
        rows.append({"section": "统计", "item": "熵(bits/byte)", "value": str(entropy)})
        encoding = "ASCII" if all(ord(char) < 128 for char in text) else "UTF-8（含非 ASCII 字符）"
        rows.append({"section": "编码", "item": "候选编码", "value": encoding})
        frequency = Counter(text)
        for char, count in frequency.most_common(top_n):
            rows.append(
                {
                    "section": "频率",
                    "item": repr(char),
                    "value": f"{count} 次（{count / max(1, len(text)) * 100:.2f}%）",
                }
            )
        context.info(f"{self.id} 完成：{len(rows)} 行")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"文本分析完成：{len(text)} 字符，熵 {entropy} bits/byte。",
            data=rows,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
