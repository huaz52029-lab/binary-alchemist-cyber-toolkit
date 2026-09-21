"""Base58 encode/decode tool (Bitcoin alphabet, pure Python)."""

from __future__ import annotations

from typing import ClassVar

from core.tool_definition import ToolCategory, ToolDefinition, ToolParameter, ToolParameterKind
from modules.encoding.base import EncodingTool


class Base58Tool(EncodingTool):
    codec_name = "base58"

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="encoding.base58",
        name="Base58",
        category=ToolCategory.ENCODING,
        icon="encoding",
        description="Base58 编码/解码（Bitcoin 字母表，纯 Python 实现）。编码而非加密。",
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
