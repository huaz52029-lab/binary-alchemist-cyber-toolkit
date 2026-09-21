"""Text / Unicode-escape conversion tool."""

from __future__ import annotations

from typing import ClassVar

from core.tool_definition import ToolCategory, ToolDefinition, ToolParameter, ToolParameterKind
from modules.encoding.base import EncodingTool


class UnicodeTool(EncodingTool):
    codec_name = "unicode"

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="encoding.unicode",
        name="Unicode",
        category=ToolCategory.ENCODING,
        icon="encoding",
        description="文本与 Unicode 转义（\\uXXXX / \\UXXXXXXXX）互转，支持中文与 Emoji。",
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
