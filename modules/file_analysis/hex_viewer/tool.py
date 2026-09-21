"""FileHexViewerTool: paged, read-only hex dump and ASCII/hex search."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from core.exceptions import FileSystemError, ToolInputError
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
from infrastructure.filesystem import iter_chunks, read_region

DISPLAY_SPEC: dict[str, Any] = {
    "title": "Hex Viewer",
    "table": {
        "columns": [
            {"field": "offset", "label": "Offset"},
            {"field": "hex", "label": "Hex"},
            {"field": "ascii", "label": "ASCII"},
        ]
    },
}


def hexdump_lines(data: bytes, base_offset: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index in range(0, len(data), 16):
        block = data[index : index + 16]
        rows.append(
            {
                "offset": f"{base_offset + index:08X}",
                "hex": " ".join(f"{byte:02X}" for byte in block),
                "ascii": "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in block),
            }
        )
    return rows


def _parse_offset(value: str) -> int:
    stripped = value.strip()
    if not stripped:
        raise ToolInputError("empty offset", user_message="请输入要跳转的偏移量。")
    try:
        return int(stripped, 16) if stripped.lower().startswith("0x") else int(stripped)
    except ValueError as exc:
        raise ToolInputError(
            f"invalid offset: {stripped}",
            user_message="偏移量无效，请输入十进制或 0x 开头的十六进制。",
        ) from exc


class FileHexViewerTool(BaseTool):
    """Hex Viewer：分页只读查看文件十六进制内容，支持偏移跳转与搜索。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="file_analysis.hex_viewer",
        name="Hex Viewer",
        category=ToolCategory.FILE_ANALYSIS,
        icon="file",
        description="分页查看文件十六进制数据（只读，不可修改），支持 ASCII/Hex 搜索。",
        parameters=[
            ToolParameter(
                name="file_path",
                label="文件",
                kind=ToolParameterKind.FILE,
                placeholder="选择要查看的文件",
            ),
            ToolParameter(name="offset", label="偏移量", placeholder="0 或 0x1000"),
            ToolParameter(
                name="length",
                label="每页字节数",
                kind=ToolParameterKind.INTEGER,
                default=256,
                minimum=16,
                maximum=4096,
            ),
            ToolParameter(name="search", label="搜索内容", placeholder="留空则显示数据"),
            ToolParameter(
                name="search_mode",
                label="搜索模式",
                kind=ToolParameterKind.CHOICE,
                default="ascii",
                choices=["ascii", "hex"],
                choice_labels=["ASCII 文本", "Hex 字节"],
            ),
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw_path = str(params.get("file_path", "")).strip()
        if not raw_path:
            return context.make_result(ResultStatus.FAILED, "请选择要查看的文件。")
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            return context.make_result(ResultStatus.FAILED, "文件不存在。")
        try:
            offset = _parse_offset(str(params.get("offset", "0")))
        except ToolInputError as exc:
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        search = str(params.get("search", "")).strip()
        try:
            if search:
                return self._search(path, search, str(params.get("search_mode", "ascii")), context)
            data = read_region(path, offset, int(params.get("length", 256)))
        except (FileSystemError, ToolInputError, ValueError) as exc:
            if isinstance(exc, ToolInputError):
                return context.make_result(ResultStatus.FAILED, exc.user_message)
            if isinstance(exc, ValueError):
                return context.make_result(ResultStatus.FAILED, "搜索内容不是有效的Hex字节。")
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        context.info(f"{self.id} 显示 {len(data)} 字节 @0x{offset:X}")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"偏移 0x{offset:X} 起共 {len(data)} 字节。",
            data=hexdump_lines(data, offset),
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )

    def _search(
        self,
        path: Path,
        search: str,
        mode: str,
        context: ExecutionContext,
    ) -> ToolResult:
        if mode == "hex":
            try:
                needle = bytes.fromhex("".join(search.split()))
            except ValueError:
                return context.make_result(ResultStatus.FAILED, "搜索内容不是有效的Hex字节。")
        else:
            needle = search.encode("utf-8")
        if not needle:
            return context.make_result(ResultStatus.FAILED, "搜索内容不能为空。")
        matches: list[dict[str, str]] = []
        base = 0
        carry = b""
        for chunk in iter_chunks(path, is_cancelled=lambda: context.is_cancelled):
            data = carry + chunk
            start = 0
            while len(matches) < 1000:
                found = data.find(needle, start)
                if found == -1:
                    break
                absolute = base - len(carry) + found
                context_bytes = read_region(path, absolute, 16)
                matches.append(
                    {
                        "offset": f"{absolute:08X}",
                        "hex": " ".join(f"{byte:02X}" for byte in context_bytes),
                        "ascii": "".join(
                            chr(byte) if 32 <= byte <= 126 else "." for byte in context_bytes
                        ),
                    }
                )
                start = found + max(1, len(needle))
            if len(matches) >= 1000:
                break
            carry = data[-max(0, len(needle) - 1) :]
            base += len(chunk)
        context.info(f"{self.id} 搜索完成：{len(matches)} 处匹配")
        summary = f"找到 {len(matches)} 处匹配（最多显示 1000）。" if matches else "未找到匹配。"
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=matches,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
