"""Text/binary (0/1) conversion tool."""

from __future__ import annotations

from typing import ClassVar

from core.tool_definition import ToolCategory, ToolDefinition, ToolParameter, ToolParameterKind
from modules.encoding.base import EncodingTool


class BinaryTool(EncodingTool):
    codec_name = "binary"

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="encoding.binary",
        name="Binary",
        category=ToolCategory.ENCODING,
        icon="encoding",
        description="文本与 8 位二进制（0/1）互转，解码支持空格分隔。",
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
