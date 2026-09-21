"""Base64 encode/decode tool."""

from __future__ import annotations

from typing import ClassVar

from core.tool_definition import ToolCategory, ToolDefinition, ToolParameter, ToolParameterKind
from modules.encoding.base import EncodingTool


class Base64Tool(EncodingTool):
    codec_name = "base64"

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="encoding.base64",
        name="Base64",
        category=ToolCategory.ENCODING,
        icon="encoding",
        description="Base64 编码/解码（UTF-8 文本）。Base64 是编码而非加密。",
        input_policy="safe-to-persist",
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
