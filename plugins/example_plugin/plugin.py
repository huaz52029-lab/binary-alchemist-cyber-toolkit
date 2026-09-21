"""Example plugin entry point."""

from __future__ import annotations

from typing import Any, ClassVar

from core.plugin_sdk import (
    BaseTool,
    ExecutionContext,
    PluginContext,
    ResultStatus,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolParameterKind,
    ToolParameters,
    ToolResult,
)

DISPLAY_SPEC: dict[str, Any] = {
    "title": "文本统计（示例插件）",
    "sections": [
        {
            "title": "结果",
            "items": [
                {"field": "characters", "label": "字符数量"},
                {"field": "bytes", "label": "字节数量"},
                {"field": "lines", "label": "行数"},
            ],
        }
    ],
}


class TextStatsTool(BaseTool):
    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="text.stats",
        name="文本统计",
        category=ToolCategory.CTF,
        icon="ctf",
        description="示例插件工具：统计输入文本的字符数、字节数与行数。",
        parameters=[
            ToolParameter(
                name="input",
                label="文本",
                kind=ToolParameterKind.MULTILINE,
                placeholder="输入任意文本",
            )
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        text = str(params.get("input", ""))
        data = text.encode("utf-8")
        context.info(f"text.stats 分析 {len(text)} 字符")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"{len(text)} 字符 / {len(data)} 字节 / {text.count(chr(10)) + (1 if text else 0)} 行",
            data=[
                {
                    "characters": len(text),
                    "bytes": len(data),
                    "lines": text.count("\n") + (1 if text else 0),
                }
            ],
            metadata={
                "tool_id": self.definition.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )


def register(context: PluginContext) -> list[BaseTool]:
    """Official plugin entry point."""
    context.logger.info("Example plugin register()")
    return [TextStatsTool()]
