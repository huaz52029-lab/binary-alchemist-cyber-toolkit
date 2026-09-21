"""ROT47 tool (ASCII 33-126, self-inverse)."""

from __future__ import annotations

from typing import ClassVar

from core.tool_definition import ToolCategory, ToolDefinition, ToolParameter, ToolParameterKind
from modules.encoding.base import EncodingTool


class Rot47Tool(EncodingTool):
    codec_name = "rot47"

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="encoding.rot47",
        name="ROT47",
        category=ToolCategory.ENCODING,
        icon="encoding",
        description="ROT47 旋转（ASCII 33-126，范围外字符保持不变，自身可逆）。",
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
