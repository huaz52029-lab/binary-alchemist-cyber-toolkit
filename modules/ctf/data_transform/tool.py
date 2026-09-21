"""DataTransformTool: text/bytes/hex/integer/binary/base64 conversions."""

from __future__ import annotations

import base64
from typing import Any, ClassVar, Literal

from core.exceptions import ToolInputError
from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext
from core.tool_definition import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolParameterKind,
    ToolParameters,
)

DISPLAY_SPEC: dict[str, Any] = {
    "title": "数据转换",
    "sections": [
        {
            "title": "结果",
            "items": [
                {"field": "conversion", "label": "转换"},
                {"field": "result", "label": "结果"},
                {"field": "bytes_hex", "label": "中间字节(Hex)"},
            ],
        }
    ],
}


def _parse_int(value: str) -> int:
    try:
        return int(value.strip())
    except ValueError as exc:
        raise ToolInputError("not an integer", user_message="整数输入无效。") from exc


def _to_bytes(value: int, endian: str) -> bytes:
    length = max(1, (value.bit_length() + 7) // 8)
    byte_order: Literal["big", "little"] = "big" if endian == "big" else "little"
    try:
        return value.to_bytes(length, byte_order)
    except OverflowError as exc:
        raise ToolInputError("integer too large", user_message="整数超出可表示范围。") from exc


class DataTransformTool(BaseTool):
    """数据转换：Text/Bytes/Hex/Integer/Binary/Base64 双向转换（支持大小端）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="ctf.data_transform",
        name="数据转换",
        category=ToolCategory.CTF,
        icon="ctf",
        description="文本、字节、Hex、整数、二进制与 Base64 之间的双向转换。",
        parameters=[
            ToolParameter(
                name="input",
                label="输入",
                kind=ToolParameterKind.MULTILINE,
                placeholder="输入要转换的数据",
            ),
            ToolParameter(
                name="source",
                label="输入类型",
                kind=ToolParameterKind.CHOICE,
                default="text",
                choices=["text", "hex", "base64", "integer"],
                choice_labels=["文本", "Hex", "Base64", "整数"],
            ),
            ToolParameter(
                name="target",
                label="目标类型",
                kind=ToolParameterKind.CHOICE,
                default="hex",
                choices=["text", "hex", "bytes", "integer", "binary", "base64"],
                choice_labels=["文本", "Hex", "字节列表", "整数", "二进制", "Base64"],
            ),
            ToolParameter(
                name="endian",
                label="字节序",
                kind=ToolParameterKind.CHOICE,
                default="big",
                choices=["big", "little"],
                choice_labels=["大端", "小端"],
            ),
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw = str(params.get("input", ""))
        source = str(params.get("source", "text"))
        target = str(params.get("target", "hex"))
        endian = str(params.get("endian", "big"))
        try:
            if source == "text":
                data = raw.encode("utf-8")
            elif source == "hex":
                data = bytes.fromhex("".join(raw.split()))
            elif source == "base64":
                data = base64.b64decode(raw.strip(), validate=True)
            else:
                data = _to_bytes(_parse_int(raw), endian)
        except (ValueError, ToolInputError) as exc:
            message = (
                exc.user_message
                if isinstance(exc, ToolInputError)
                else f"输入不是有效的 {source} 数据。"
            )
            return context.make_result(ResultStatus.FAILED, message)
        if target == "text":
            try:
                result = data.decode("utf-8")
            except UnicodeDecodeError:
                return context.make_result(ResultStatus.FAILED, "结果不是有效的 UTF-8 文本。")
        elif target == "hex":
            result = data.hex()
        elif target == "bytes":
            result = ", ".join(str(byte) for byte in data)
        elif target == "integer":
            result = str(int.from_bytes(data, "big" if endian == "big" else "little"))
        elif target == "binary":
            result = " ".join(f"{byte:08b}" for byte in data)
        else:
            result = base64.b64encode(data).decode("ascii")
        context.info(f"{self.id} 完成：{source} → {target}（{len(data)} 字节）")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"{source} → {target} 转换完成（{len(data)} 字节）。",
            data=[
                {
                    "conversion": f"{source} → {target}",
                    "result": result,
                    "bytes_hex": data.hex(),
                }
            ],
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
