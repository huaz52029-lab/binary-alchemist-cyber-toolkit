"""URL percent-encode/decode tool."""

from __future__ import annotations

from typing import ClassVar

from core.tool_definition import ToolCategory, ToolDefinition, ToolParameter, ToolParameterKind
from modules.encoding.base import EncodingTool


class UrlTool(EncodingTool):
    codec_name = "url"

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="encoding.url",
        name="URL Encode",
        category=ToolCategory.ENCODING,
        icon="encoding",
        description="URL 百分号编码/解码（urllib.parse）。URL 编码不是加密。",
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
