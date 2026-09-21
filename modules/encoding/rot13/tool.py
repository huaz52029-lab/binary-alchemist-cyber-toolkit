"""ROT13 tool (self-inverse)."""

from __future__ import annotations

from typing import ClassVar

from core.tool_definition import ToolCategory, ToolDefinition, ToolParameter, ToolParameterKind
from modules.encoding.base import EncodingTool


class Rot13Tool(EncodingTool):
    codec_name = "rot13"

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="encoding.rot13",
        name="ROT13",
        category=ToolCategory.ENCODING,
        icon="encoding",
        description="ROT13 字母旋转（自身可逆）。这是编码而非加密。",
        input_policy="safe-to-persist",
        page="encoding",
        parameters=[
            ToolParameter(
                name="operation",
                label="操作",
                kind=ToolParameterKind.CHOICE,
                default="transform",
                choices=["transform"],
                choice_labels=["转换"],
            ),
            ToolParameter(name="input", label="输入", kind=ToolParameterKind.MULTILINE),
        ],
    )
