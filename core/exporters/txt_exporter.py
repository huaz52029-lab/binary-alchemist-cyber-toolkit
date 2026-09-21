"""Human-readable plain-text export of a ToolResult."""

from __future__ import annotations

import json
from pathlib import Path

from core.result import ToolResult


class TxtExporter:
    """Renders status, findings and data as a readable text report."""

    name: str = "txt"
    extensions: tuple[str, ...] = ("txt",)

    def to_string(self, result: ToolResult) -> str:
        lines = [
            f"状态: {result.status.value}",
            f"摘要: {result.summary}",
            f"耗时: {result.duration if result.duration is not None else '未知'} 秒",
            "",
            f"发现 ({len(result.findings)}):",
        ]
        for finding in result.findings:
            lines.append(f"- [{finding.severity.value}|{finding.kind.value}] {finding.title}")
            if finding.description:
                lines.append(f"    描述: {finding.description}")
            if finding.evidence:
                lines.append(f"    证据: {finding.evidence}")
            if finding.recommendation:
                lines.append(f"    建议: {finding.recommendation}")
            if finding.source:
                lines.append(f"    来源: {finding.source}")
        lines.extend(["", f"数据 ({len(result.data)} 条):"])
        for row in result.data:
            lines.append(f"- {json.dumps(row, ensure_ascii=False)}")
        return "\n".join(lines)

    def export(self, result: ToolResult, path: Path) -> Path:
        path.write_text(self.to_string(result) + "\n", encoding="utf-8")
        return path
