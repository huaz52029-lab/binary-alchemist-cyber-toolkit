"""FileHashesTool: all six digests in a single streaming pass."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any, ClassVar

from core.exceptions import FileSystemError
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
from infrastructure.filesystem import human_size
from modules.crypto.hash.hasher import ALGORITHMS, hash_file_multi

DISPLAY_SPEC: dict[str, Any] = {
    "title": "文件 Hash",
    "sections": [
        {
            "title": "基本信息",
            "items": [
                {"field": "name", "label": "文件名"},
                {"field": "size", "label": "大小"},
                {"field": "elapsed_ms", "label": "耗时(ms)"},
            ],
        },
        {
            "title": "Hash",
            "items": [{"field": algorithm.lower(), "label": algorithm} for algorithm in ALGORITHMS],
        },
    ],
}


class FileHashesTool(BaseTool):
    """文件 Hash：分块流式计算 MD5/SHA1/SHA2 全部摘要。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="file_analysis.hashes",
        name="文件 Hash",
        category=ToolCategory.FILE_ANALYSIS,
        icon="file",
        description="单次流式计算文件的 MD5/SHA1/SHA224/SHA256/SHA384/SHA512（分块读取）。",
        parameters=[
            ToolParameter(
                name="file_path",
                label="文件",
                kind=ToolParameterKind.FILE,
                placeholder="选择要计算 Hash 的文件",
            )
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw_path = str(params.get("file_path", "")).strip()
        if not raw_path:
            return context.make_result(ResultStatus.FAILED, "请选择要计算 Hash 的文件。")
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            return context.make_result(ResultStatus.FAILED, "文件不存在。")
        context.info(f"{self.id} 开始计算：{path.name}")
        started = perf_counter()
        try:
            digests = hash_file_multi(
                path,
                ALGORITHMS,
                is_cancelled=lambda: context.is_cancelled,
                on_progress=lambda value: context.set_progress(value),
            )
        except FileSystemError as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        elapsed_ms = round((perf_counter() - started) * 1000.0, 2)
        row: dict[str, Any] = {
            "name": path.name,
            "size": human_size(path.stat().st_size),
            "elapsed_ms": elapsed_ms,
            **{algorithm.lower(): digests[algorithm] for algorithm in ALGORITHMS},
        }
        context.info(f"{self.id} 完成：耗时 {elapsed_ms}ms")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"{path.name} 全部 Hash 计算完成（{elapsed_ms}ms）。",
            data=[row],
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
