"""PeAnalysisTool: headers, sections, imports, exports, resources and overlay."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from core.exceptions import FileSystemError, ToolInputError
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
from modules.file_analysis.pe_analysis.pe import analyze_pe

DISPLAY_SPEC: dict[str, Any] = {
    "title": "PE 分析结果",
    "table": {
        "columns": [
            {"field": "section", "label": "分类"},
            {"field": "item", "label": "项目"},
            {"field": "value", "label": "值"},
        ]
    },
}

HIGH_ENTROPY_THRESHOLD = 7.0


class PeAnalysisTool(BaseTool):
    """PE 分析：DOS/NT/File/Optional Header、Sections、Imports、Exports、Resources、Overlay。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="file_analysis.pe_analysis",
        name="PE 分析",
        category=ToolCategory.FILE_ANALYSIS,
        icon="file",
        description="静态解析 PE 头、Section、导入/导出、资源与 Overlay（绝不执行样本）。",
        parameters=[
            ToolParameter(
                name="file_path",
                label="文件",
                kind=ToolParameterKind.FILE,
                placeholder="选择 PE 文件（EXE/DLL/SYS）",
            )
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw_path = str(params.get("file_path", "")).strip()
        if not raw_path:
            return context.make_result(ResultStatus.FAILED, "请选择要分析的 PE 文件。")
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            return context.make_result(ResultStatus.FAILED, "文件不存在。")
        context.info(f"{self.id} 开始解析：{path.name}")
        try:
            analysis = analyze_pe(path)
        except (ToolInputError, FileSystemError) as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        rows = self._build_rows(analysis)
        findings = self._build_findings(analysis)
        context.info(
            f"{self.id} 完成：{analysis.bits} {analysis.machine}，"
            f"{len(analysis.sections)} 个 Section，{len(analysis.imports)} 个导入"
        )
        return context.make_result(
            ResultStatus.SUCCESS,
            f"PE 分析完成：{analysis.bits} · {analysis.machine} · "
            f"{len(analysis.sections)} 个 Section。",
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )

    @staticmethod
    def _build_rows(analysis: Any) -> list[dict[str, str]]:
        rows = [
            {"section": "基本信息", "item": "架构", "value": f"{analysis.bits} {analysis.machine}"},
            {"section": "基本信息", "item": "时间戳(UTC)", "value": analysis.timestamp},
            {"section": "基本信息", "item": "入口点", "value": analysis.entry_point},
            {"section": "基本信息", "item": "Image Base", "value": analysis.image_base},
            {"section": "基本信息", "item": "子系统", "value": analysis.subsystem},
            {
                "section": "基本信息",
                "item": "Section 对齐",
                "value": str(analysis.section_alignment),
            },
            {"section": "基本信息", "item": "文件对齐", "value": str(analysis.file_alignment)},
            {"section": "基本信息", "item": "Section 数量", "value": str(analysis.section_count)},
            {"section": "基本信息", "item": "Characteristics", "value": analysis.characteristics},
            {"section": "DOS Header", "item": "Magic", "value": analysis.dos_magic},
            {"section": "DOS Header", "item": "e_lfanew", "value": analysis.e_lfanew},
            {"section": "NT Header", "item": "PE Signature", "value": analysis.pe_signature},
        ]
        for section in analysis.sections:
            rows.append(
                {
                    "section": f"Section:{section['name']}",
                    "item": "属性",
                    "value": (
                        f"VA={section['virtual_address']} VS={section['virtual_size']} "
                        f"RS={section['raw_size']} 熵={section['entropy']} "
                        f"执行={section['executable']} 写={section['writable']}"
                    ),
                }
            )
        for imported in analysis.imports:
            rows.append(
                {
                    "section": f"Import:{imported.dll}",
                    "item": imported.name,
                    "value": imported.category,
                }
            )
        for exported in analysis.exports:
            rows.append(
                {
                    "section": "Export",
                    "item": f"{exported['ordinal']} {exported['name']}",
                    "value": exported["address"],
                }
            )
        for resource in analysis.resources:
            rows.append(
                {
                    "section": f"Resource:{resource['type']}",
                    "item": resource["id"],
                    "value": resource["size"],
                }
            )
        rows.append(
            {
                "section": "Overlay",
                "item": "大小",
                "value": f"{analysis.overlay_size} 字节",
            }
        )
        return rows

    def _build_findings(self, analysis: Any) -> list[Finding]:
        findings: list[Finding] = []
        for section in analysis.sections:
            if section["executable"] and section["writable"]:
                findings.append(
                    Finding(
                        title="发现可执行且可写PE Section",
                        severity=Severity.MEDIUM,
                        kind=FindingKind.FACT,
                        description=f"Section「{section['name']}」同时具有执行和写入权限。",
                        evidence=section["name"],
                        recommendation="结合文件来源、代码结构和运行行为进一步分析。",
                        source=self.id,
                    )
                )
            if section["entropy"] > HIGH_ENTROPY_THRESHOLD:
                findings.append(
                    Finding(
                        title="Section 熵较高",
                        severity=Severity.INFO,
                        kind=FindingKind.HEURISTIC,
                        description=(
                            f"Section「{section['name']}」熵为 {section['entropy']}，"
                            "可能存在压缩或加密数据。"
                        ),
                        evidence=f"section={section['name']}",
                        source=self.id,
                    )
                )
        categories = {imported.category for imported in analysis.imports}
        if "Network" in categories:
            findings.append(
                Finding(
                    title="发现网络相关 API",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description="导入表中存在网络相关 API（分类：Network），仅作为分析线索。",
                    evidence="import_category=Network",
                    source=self.id,
                )
            )
        if "Process" in categories:
            findings.append(
                Finding(
                    title="发现进程相关 API",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=(
                        "导入表中存在进程创建/执行相关 API（分类：Process），仅作为分析线索。"
                    ),
                    evidence="import_category=Process",
                    source=self.id,
                )
            )
        if analysis.overlay_size > 0:
            findings.append(
                Finding(
                    title="存在 Overlay 数据",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description="文件末尾存在PE结构之外的数据。",
                    evidence=f"overlay_size={analysis.overlay_size}",
                    source=self.id,
                )
            )
        return findings
