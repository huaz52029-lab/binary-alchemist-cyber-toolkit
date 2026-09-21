"""Text / HTML entity conversion tool."""

from __future__ import annotations

from typing import ClassVar

from core.tool_definition import ToolCategory, ToolDefinition, ToolParameter, ToolParameterKind
from modules.encoding.base import EncodingTool


class HtmlEntityTool(EncodingTool):
    codec_name = "html_entity"

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="encoding.html_entity",
        name="HTML Entity",
        category=ToolCategory.ENCODING,
        icon="encoding",
        description="文本与 HTML 实体（&lt; 等）互转。",
        page="encoding",
        parameters=[
            ToolParameter(
                name="operation",
                label="操作",
                kind=ToolParameterKind.CHOICE,
                default="encode",
                choices=["encode", "decode"],
                choice_labels=["编码", "解码"],
            ),
            ToolParameter(name="input", label="输入", kind=ToolParameterKind.MULTILINE),
        ],
    )
