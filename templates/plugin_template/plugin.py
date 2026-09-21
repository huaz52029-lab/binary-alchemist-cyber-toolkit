"""My Plugin entry point."""

from __future__ import annotations

from typing import ClassVar

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


class MyTool(BaseTool):
    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="my_tool",
        name="My Tool",
        category=ToolCategory.CTF,
        description="我的插件工具",
        parameters=[
            ToolParameter(
                name="input",
                label="输入",
                kind=ToolParameterKind.MULTILINE,
                placeholder="输入文本",
            )
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        text = str(params.get("input", ""))
        context.info(f"my_tool 处理 {len(text)} 字符")
        return context.make_result(ResultStatus.SUCCESS, f"处理了 {len(text)} 字符。")


def register(context: PluginContext) -> list[BaseTool]:
    context.logger.info("register my plugin tools")
    return [MyTool()]
