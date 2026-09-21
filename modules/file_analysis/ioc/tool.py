"""FileIocTool: candidate IOC extraction from extracted strings."""

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
from modules.file_analysis.ioc.extractor import extract_iocs
from modules.file_analysis.strings.extractor import extract_strings

DISPLAY_SPEC: dict[str, Any] = {
    "title": "Candidate IOC",
    "table": {
        "columns": [
            {"field": "type", "label": "类型"},
            {"field": "value", "label": "值"},
            {"field": "note", "label": "属性"},
            {"field": "context", "label": "上下文"},
        ]
    },
}


class FileIocTool(BaseTool):
    """IOC 候选提取：从字符串中提取 IP/URL/域名/邮箱/路径/注册表（均为候选）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="file_analysis.ioc",
        name="IOC 候选提取",
        category=ToolCategory.FILE_ANALYSIS,
        icon="file",
        description="从文件字符串中提取 IPv4/IPv6、URL、域名、邮箱、Windows 路径与注册表路径候选。",
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
        context.info(f"{self.id} 开始提取：{path.name}")
        try:
            records = extract_strings(
                path,
                encoding="utf8",
                min_length=4,
                is_cancelled=lambda: context.is_cancelled,
            )
        except FileSystemError as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        iocs = extract_iocs("\n".join(record.text for record in records))
        context.info(f"{self.id} 完成：{len(iocs)} 个候选 IOC")
        findings: list[Finding] = []
        if iocs:
            findings.append(
                Finding(
                    title="发现候选 IOC",
                    severity=Severity.INFO,
                    kind=FindingKind.HEURISTIC,
                    description=(
                        f"从文件字符串中提取到 {len(iocs)} 个候选 IOC。"
                        "这些均为候选，需结合上下文判断，不能据此判定文件恶意。"
                    ),
                    evidence=f"ioc_count={len(iocs)}",
                    source=self.id,
                )
            )
        return context.make_result(
            ResultStatus.SUCCESS,
            f"提取到 {len(iocs)} 个候选 IOC（Candidate IOC，非恶意判定）。",
            data=iocs,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
