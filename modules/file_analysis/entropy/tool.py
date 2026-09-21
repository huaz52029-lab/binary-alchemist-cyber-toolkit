"""FileEntropyTool: whole-file entropy plus PE section entropy."""

from __future__ import annotations

from collections import Counter
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
from infrastructure.filesystem import human_size, iter_chunks
from modules.file_analysis.entropy.analyzer import entropy_from_bytes, shannon_entropy

SECTION_DISPLAY_SPEC: dict[str, Any] = {
    "title": "Section 熵",
    "table": {
        "columns": [
            {"field": "section", "label": "Section"},
            {"field": "entropy", "label": "熵(bits/byte)"},
        ]
    },
}

FULL_DISPLAY_SPEC: dict[str, Any] = {
    "title": "文件熵",
    "sections": [
        {
            "title": "结果",
            "items": [
                {"field": "name", "label": "文件名"},
                {"field": "size", "label": "大小"},
                {"field": "entropy", "label": "整体熵(bits/byte)"},
            ],
        }
    ],
}

HIGH_ENTROPY_THRESHOLD = 7.0


class FileEntropyTool(BaseTool):
    """文件熵分析：Shannon 熵（0-8 bits/byte），PE 附带 Section 级熵。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="file_analysis.entropy",
        name="文件熵分析",
        category=ToolCategory.FILE_ANALYSIS,
        icon="file",
        description="计算文件 Shannon 熵；高熵仅提示可能存在压缩/加密/打包数据。",
        parameters=[
            ToolParameter(
                name="file_path",
                label="文件",
                kind=ToolParameterKind.FILE,
                placeholder="选择要分析的文件",
            )
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw_path = str(params.get("file_path", "")).strip()
        if not raw_path:
            return context.make_result(ResultStatus.FAILED, "请选择要分析的文件。")
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            return context.make_result(ResultStatus.FAILED, "文件不存在。")
        context.info(f"{self.id} 开始计算：{path.name}")
        counts: Counter[int] = Counter()
        total = 0
        try:
            for chunk in iter_chunks(path, is_cancelled=lambda: context.is_cancelled):
                counts.update(chunk)
                total += len(chunk)
                context.set_progress(None, f"已读取 {human_size(total)}")
        except FileSystemError as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        entropy = round(shannon_entropy(counts, total), 4)
        findings: list[Finding] = []
        if entropy > HIGH_ENTROPY_THRESHOLD:
            findings.append(
                Finding(
                    title="文件整体熵较高",
                    severity=Severity.LOW,
                    kind=FindingKind.HEURISTIC,
                    description=(
                        f"整体熵为 {entropy} bits/byte，可能与压缩、加密、打包或随机数据有关。"
                        "高熵不能直接判定恶意。"
                    ),
                    evidence=f"entropy={entropy}",
                    source=self.id,
                )
            )
        sections = self._pe_section_entropy(path)
        for section in sections:
            if section["entropy"] > HIGH_ENTROPY_THRESHOLD:
                findings.append(
                    Finding(
                        title=f"Section「{section['section']}」熵较高",
                        severity=Severity.INFO,
                        kind=FindingKind.HEURISTIC,
                        description=(
                            f"该 Section 熵为 {section['entropy']} bits/byte，"
                            "可能存在压缩或加密数据。"
                        ),
                        evidence=f"section={section['section']}",
                        source=self.id,
                    )
                )
        context.info(f"{self.id} 完成：整体熵 {entropy}")
        if sections:
            return context.make_result(
                ResultStatus.SUCCESS,
                f"整体熵 {entropy} bits/byte，另计算 {len(sections)} 个 Section 熵。",
                data=sections,
                findings=findings,
                metadata={
                    "tool_id": self.id,
                    "tool_version": self.definition.version,
                    "display": SECTION_DISPLAY_SPEC,
                },
            )
        return context.make_result(
            ResultStatus.SUCCESS,
            f"整体熵 {entropy} bits/byte（0-8）。",
            data=[
                {
                    "name": path.name,
                    "size": human_size(total),
                    "entropy": entropy,
                }
            ],
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": FULL_DISPLAY_SPEC,
            },
        )

    @staticmethod
    def _pe_section_entropy(path: Path) -> list[dict[str, Any]]:
        try:
            import pefile

            pe = pefile.PE(str(path), fast_load=True)
        except Exception:  # non-PE or malformed: entropy tool keeps going
            return []
        sections: list[dict[str, Any]] = []
        for section in pe.sections:
            try:
                data = section.get_data()
            except Exception:  # pragma: no cover - defensive
                continue
            if data:
                sections.append(
                    {
                        "section": section.Name.rstrip(b"\x00").decode("utf-8", errors="replace"),
                        "entropy": round(entropy_from_bytes(data), 4),
                    }
                )
        pe.close()
        return sections
