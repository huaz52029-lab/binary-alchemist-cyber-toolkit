"""FileStringsTool: printable strings with keyword hints."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from core.exceptions import FileSystemError
from core.finding import Finding, FindingKind, Severity
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
from modules.file_analysis.strings.extractor import extract_strings, keyword_hints

DISPLAY_SPEC: dict[str, Any] = {
    "title": "字符串提取结果",
    "table": {
        "columns": [
            {"field": "offset", "label": "Offset"},
            {"field": "encoding", "label": "编码"},
            {"field": "length", "label": "长度"},
            {"field": "text", "label": "字符串"},
            {"field": "hints", "label": "线索"},
        ]
    },
}


class FileStringsTool(BaseTool):
    """字符串提取：从二进制文件流式提取 ASCII/UTF-8/UTF-16LE 字符串。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="file_analysis.strings",
        name="字符串提取",
        category=ToolCategory.FILE_ANALYSIS,
        icon="file",
        description="流式提取文件中的可读字符串并标注分析线索（不据此判定恶意）。",
        parameters=[
            ToolParameter(
                name="file_path",
                label="文件",
                kind=ToolParameterKind.FILE,
                placeholder="选择要扫描的文件",
            ),
            ToolParameter(
                name="min_length",
                label="最小长度",
                kind=ToolParameterKind.INTEGER,
                default=4,
                minimum=4,
                maximum=100,
            ),
            ToolParameter(
                name="encoding",
                label="编码",
                kind=ToolParameterKind.CHOICE,
                default="ascii",
                choices=["ascii", "utf8", "utf16le"],
                choice_labels=["ASCII", "UTF-8", "UTF-16LE"],
            ),
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw_path = str(params.get("file_path", "")).strip()
        if not raw_path:
            return context.make_result(ResultStatus.FAILED, "请选择要扫描的文件。")
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            return context.make_result(ResultStatus.FAILED, "文件不存在。")
        min_length = int(params.get("min_length", 4))
        encoding = str(params.get("encoding", "ascii"))
        context.info(f"{self.id} 开始提取：{path.name}（{encoding}，最小长度 {min_length}）")
        try:
            records = extract_strings(
                path,
                encoding=encoding,
                min_length=min_length,
                is_cancelled=lambda: context.is_cancelled,
                on_progress=lambda _offset: context.set_progress(None),
            )
        except FileSystemError as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        rows = [
            {
                "offset": f"0x{record.offset:08X}",
                "encoding": record.encoding,
                "length": record.length,
                "text": record.text,
                "hints": ", ".join(keyword_hints(record.text)) or "-",
            }
            for record in records
        ]
        findings = self._keyword_findings(records)
        context.info(f"{self.id} 完成：提取 {len(records)} 条字符串")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"提取到 {len(records)} 条 {encoding} 字符串。",
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )

    def _keyword_findings(self, records: list[Any]) -> list[Finding]:
        matched = sorted({hint for record in records for hint in keyword_hints(record.text)})
        if not matched:
            return []
        return [
            Finding(
                title="发现分析线索字符串",
                severity=Severity.INFO,
                kind=FindingKind.HEURISTIC,
                description=(
                    f"字符串中包含以下线索关键词：{', '.join(matched)}。"
                    "这些只是静态分析线索，不能单独作为恶意判定依据。"
                ),
                evidence=f"keywords={', '.join(matched)}",
                source=self.id,
            )
        ]
