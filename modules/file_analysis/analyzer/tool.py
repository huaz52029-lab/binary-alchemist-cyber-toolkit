"""FileAnalyzerTool: composite static analysis of a single file."""

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
from infrastructure.filesystem import (
    FileTypeDetector,
    file_snapshot,
    human_size,
    iter_chunks,
)
from modules.crypto.hash.hasher import hash_file
from modules.file_analysis.entropy.analyzer import shannon_entropy
from modules.file_analysis.ioc.extractor import extract_iocs
from modules.file_analysis.pe_analysis.pe import analyze_pe
from modules.file_analysis.strings.extractor import extract_strings

DISPLAY_SPEC: dict[str, Any] = {
    "title": "文件安全分析",
    "table": {
        "columns": [
            {"field": "section", "label": "分类"},
            {"field": "item", "label": "项目"},
            {"field": "value", "label": "值"},
        ]
    },
}

MAX_STRING_ROWS = 50


class FileAnalyzerTool(BaseTool):
    """文件安全分析：信息、类型、Hash、字符串、熵、IOC，PE 时含结构分析。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="file_analysis.analyzer",
        name="文件安全分析",
        category=ToolCategory.FILE_ANALYSIS,
        icon="file",
        description="对单个文件执行静态综合分析（信息/类型/Hash/字符串/熵/IOC/PE）。绝不执行样本。",
        parameters=[
            ToolParameter(
                name="file_path",
                label="文件",
                kind=ToolParameterKind.FILE,
                placeholder="选择或拖入要分析的文件",
            )
        ],
    )

    def __init__(self, detector: FileTypeDetector | None = None) -> None:
        self._detector = detector or FileTypeDetector()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw_path = str(params.get("file_path", "")).strip()
        if not raw_path:
            return context.make_result(ResultStatus.FAILED, "请选择要分析的文件。")
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            return context.make_result(ResultStatus.FAILED, "文件不存在。")
        before = file_snapshot(path)
        context.info(f"{self.id} 开始综合分析：{path.name}")
        rows: list[dict[str, Any]] = []
        findings: list[Finding] = []
        try:
            detected = self._detector.detect(path)
            rows.append({"section": "文件", "item": "名称", "value": path.name})
            rows.append(
                {"section": "文件", "item": "大小", "value": human_size(path.stat().st_size)}
            )
            rows.append({"section": "类型", "item": "检测类型", "value": detected.detected_type})
            rows.append(
                {
                    "section": "类型",
                    "item": "Magic Bytes",
                    "value": detected.magic_hex or "（文本）",
                }
            )
            rows.append({"section": "类型", "item": "说明", "value": detected.description})
            extension_type = self._detector.expected_from_extension(path.name)
            if (
                extension_type
                and detected.detected_type not in ("Unknown", "Text")
                and extension_type != detected.detected_type
            ):
                findings.append(
                    Finding(
                        title="文件扩展名与文件实际结构不一致",
                        severity=Severity.LOW,
                        kind=FindingKind.FACT,
                        description=(
                            f"扩展名推断为 {extension_type}，Magic Bytes 检测为 "
                            f"{detected.detected_type}。这只是结构不一致，不代表文件恶意。"
                        ),
                        evidence=f"extension={extension_type}, magic={detected.detected_type}",
                        source=self.id,
                    )
                )
            sha256 = hash_file(
                path,
                "SHA256",
                is_cancelled=lambda: context.is_cancelled,
                on_progress=lambda value: context.set_progress(value),
            )
            rows.append({"section": "Hash", "item": "SHA256", "value": sha256})
            md5 = hash_file(path, "MD5", is_cancelled=lambda: context.is_cancelled)
            rows.append({"section": "Hash", "item": "MD5", "value": md5})
            records = extract_strings(
                path,
                encoding="ascii",
                min_length=4,
                is_cancelled=lambda: context.is_cancelled,
            )
            for record in records[:MAX_STRING_ROWS]:
                rows.append(
                    {
                        "section": "Strings",
                        "item": f"0x{record.offset:08X}",
                        "value": record.text[:200],
                    }
                )
            if len(records) > MAX_STRING_ROWS:
                rows.append(
                    {
                        "section": "Strings",
                        "item": "（截断）",
                        "value": f"仅展示前 {MAX_STRING_ROWS} 条，共 {len(records)} 条",
                    }
                )
            counts = [0] * 256
            total = 0
            for chunk in iter_chunks(path, is_cancelled=lambda: context.is_cancelled):
                for byte in chunk:
                    counts[byte] += 1
                total += len(chunk)
            entropy = round(shannon_entropy(counts, total), 4)
            rows.append({"section": "Entropy", "item": "整体熵", "value": str(entropy)})
            if entropy > 7.0:
                findings.append(
                    Finding(
                        title="文件整体熵较高",
                        severity=Severity.LOW,
                        kind=FindingKind.HEURISTIC,
                        description="整体熵较高，可能与压缩、加密、打包或随机数据有关。高熵不能直接判定恶意。",
                        evidence=f"entropy={entropy}",
                        source=self.id,
                    )
                )
            iocs = extract_iocs("\n".join(record.text for record in records))
            for ioc in iocs[:50]:
                rows.append(
                    {
                        "section": "IOC",
                        "item": f"{ioc['type']} {ioc['note']}",
                        "value": ioc["value"],
                    }
                )
            if iocs:
                findings.append(
                    Finding(
                        title="发现候选 IOC",
                        severity=Severity.INFO,
                        kind=FindingKind.HEURISTIC,
                        description=f"提取到 {len(iocs)} 个候选 IOC，需结合上下文判断。",
                        evidence=f"ioc_count={len(iocs)}",
                        source=self.id,
                    )
                )
            pe_rows: list[dict[str, Any]] = []
            pe_findings: list[Finding] = []
            if detected.detected_type == "PE":
                try:
                    pe_analysis = analyze_pe(path)
                    from modules.file_analysis.pe_analysis.tool import PeAnalysisTool

                    pe_rows = PeAnalysisTool._build_rows(pe_analysis)
                    pe_findings = PeAnalysisTool()._build_findings(pe_analysis)
                except ToolInputError as exc:
                    rows.append({"section": "PE", "item": "解析失败", "value": exc.user_message})
            rows.extend(pe_rows)
            findings.extend(pe_findings)
        except FileSystemError as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        after = file_snapshot(path)
        if before != after:
            findings.append(
                Finding(
                    title="分析期间文件发生变化",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description="分析期间文件的大小或修改时间发生变化，结果可能不一致。",
                    evidence=f"before={before}, after={after}",
                    source=self.id,
                )
            )
        findings.append(
            Finding(
                title="静态分析说明",
                severity=Severity.INFO,
                kind=FindingKind.FACT,
                description="以上为静态分析结果，不代表对文件恶意性的最终判定。",
                source=self.id,
            )
        )
        summary = (
            f"文件类型 {detected.detected_type} · SHA256 {sha256[:12]}… · "
            f"候选 IOC {len(iocs)} · 提示 {len(findings)} 项（静态分析，不代表恶意性最终判定）"
        )
        context.info(
            f"{self.id} 完成：类型 {detected.detected_type}，IOC {len(iocs)}，"
            f"Finding {len(findings)}"
        )
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
