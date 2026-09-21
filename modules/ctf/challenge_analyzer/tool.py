"""ChallengeAnalyzerTool: candidate classification and tool recommendations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, ClassVar

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
from infrastructure.filesystem import FileTypeDetector

DISPLAY_SPEC: dict[str, Any] = {
    "title": "题目候选分类",
    "table": {
        "columns": [
            {"field": "section", "label": "类别"},
            {"field": "item", "label": "项目"},
            {"field": "value", "label": "值"},
        ]
    },
}

_RSA_PATTERN = re.compile(r"\b[nedpq]\s*=\s*\d{3,}\b")
_JWT_PATTERN = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")
_FLAG_PATTERN = re.compile(r"(?:flag|ctf|BA)\{[^}\r\n]+\}")


class ChallengeAnalyzerTool(BaseTool):
    """Challenge Analyzer：对输入内容做候选题型分类并推荐现有工具。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="ctf.challenge_analyzer",
        name="Challenge Analyzer",
        category=ToolCategory.CTF,
        icon="ctf",
        description="对文本/文件做候选题型分类（Encoding/Crypto/Web/Reverse/Misc/Forensics）并推荐工具。",
        parameters=[
            ToolParameter(
                name="text",
                label="文本内容（可选）",
                kind=ToolParameterKind.MULTILINE,
                placeholder="粘贴题目文本；使用文件时可留空",
            ),
            ToolParameter(
                name="file_path",
                label="文件（可选）",
                kind=ToolParameterKind.FILE,
                placeholder="选择题目附件（只读，绝不执行）",
            ),
        ],
    )

    def __init__(self, detector: FileTypeDetector | None = None) -> None:
        self._detector = detector or FileTypeDetector()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        rows: list[dict[str, Any]] = []
        recommendations: list[tuple[str, str, str]] = []
        text = str(params.get("text", ""))
        raw_path = str(params.get("file_path", "")).strip()
        if raw_path:
            path = Path(raw_path)
            if not path.is_file():
                return context.make_result(ResultStatus.FAILED, "文件不存在。")
            detected = self._detector.detect(path)
            rows.append({"section": "文件", "item": "类型", "value": detected.detected_type})
            if detected.detected_type == "PE":
                rows.append({"section": "候选分类", "item": "Reverse / Forensics", "value": "High"})
                recommendations.append(("file_analysis.pe_analysis", "PE 分析", "检测到 PE 文件"))
            elif detected.detected_type == "ELF":
                rows.append({"section": "候选分类", "item": "Reverse / Pwn", "value": "High"})
                recommendations.append(("file_analysis.file_info", "文件信息", "检测到 ELF 文件"))
            elif detected.detected_type in ("ZIP", "GZIP", "RAR", "PDF"):
                rows.append({"section": "候选分类", "item": "Misc / Forensics", "value": "Medium"})
                recommendations.append(
                    ("file_analysis.file_info", "文件信息", "检测到文档/压缩文件")
                )
            elif detected.detected_type == "Text":
                text = path.read_text(encoding="utf-8", errors="replace")
            else:
                rows.append({"section": "候选分类", "item": "Unknown", "value": "Low"})
            recommendations.append(("file_analysis.analyzer", "文件安全分析", "建议静态分析附件"))
        self._classify_text(text, rows, recommendations)
        for tool_id, name, reason in recommendations:
            rows.append({"section": "建议工具", "item": f"{name}（{tool_id}）", "value": reason})
        findings = [
            Finding(
                title="分类为候选类型",
                severity=Severity.INFO,
                kind=FindingKind.HEURISTIC,
                description="以上分类为特征启发式候选，不代表题目一定属于该类；建议结合题目描述判断。",
                source=self.id,
            )
        ]
        context.info(f"{self.id} 完成：{len(rows)} 行，{len(recommendations)} 个建议")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"给出 {len(rows)} 项候选分类与 {len(recommendations)} 个工具建议（仅为候选）。",
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )

    @staticmethod
    def _classify_text(
        text: str,
        rows: list[dict[str, Any]],
        recommendations: list[tuple[str, str, str]],
    ) -> None:
        stripped = text.strip()
        if not stripped:
            return
        if _RSA_PATTERN.search(stripped):
            rows.append({"section": "候选分类", "item": "Crypto / RSA", "value": "High"})
            recommendations.append(("crypto.rsa_helper", "RSA 辅助", "检测到 n/e/p/q 参数"))
        if _JWT_PATTERN.match(stripped):
            rows.append({"section": "候选分类", "item": "Web / Crypto", "value": "High"})
            recommendations.append(("crypto.jwt", "JWT 解析器", "检测到 JWT 结构"))
        if _FLAG_PATTERN.search(stripped):
            rows.append({"section": "候选分类", "item": "Misc", "value": "Medium"})
            recommendations.append(("ctf.flag_tools", "Flag 提取", "检测到 Flag 格式"))
        compact = "".join(stripped.split())
        if re.fullmatch(r"[0-9a-fA-F]{32}", compact):
            rows.append({"section": "候选分类", "item": "Crypto / Hash", "value": "Medium"})
            recommendations.append(
                ("crypto.hash", "Hash 计算器", "检测到 32 位 Hex（可能是 MD5 或其他 32 位数据）")
            )
        elif re.fullmatch(r"[0-9a-fA-F]{40,128}", compact):
            rows.append({"section": "候选分类", "item": "Crypto / Hash", "value": "Medium"})
            recommendations.append(("crypto.hash", "Hash 计算器", "检测到 SHA 长度 Hex"))
        elif re.fullmatch(r"[0-9a-fA-F]+", compact) and len(compact) % 2 == 0:
            rows.append({"section": "候选分类", "item": "Encoding", "value": "Medium"})
        if re.fullmatch(r"[A-Za-z0-9+/=]+", stripped) and len(stripped) % 4 == 0:
            rows.append({"section": "候选分类", "item": "Encoding", "value": "Medium"})
            recommendations.append(("ctf.auto_decode", "Auto Decode", "疑似 Base64"))
        if not rows:
            rows.append({"section": "候选分类", "item": "Unknown", "value": "Low"})
            recommendations.append(("ctf.auto_decode", "Auto Decode", "建议尝试自动解码"))
