"""Hex encode/decode tool."""

from __future__ import annotations

from typing import ClassVar

from core.tool_definition import ToolCategory, ToolDefinition, ToolParameter, ToolParameterKind
from modules.encoding.base import EncodingTool


class HexTool(EncodingTool):
    codec_name = "hex"

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="encoding.hex",
        name="Hex",
        category=ToolCategory.ENCODING,
        icon="encoding",
        description="文本与十六进制互转（支持空格分隔、大小写不敏感）。",
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
