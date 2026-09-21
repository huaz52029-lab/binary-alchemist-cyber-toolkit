"""ReportRenderer: Report -> Markdown (HTML/PDF interfaces reserved)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from core.reports.report import Report, load_template

SEVERITY_ORDER = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")


class ReportRenderer:
    """Renders a report with referenced task summaries and findings."""

    def render(self, report: Report, history_manager: Any) -> str:
        spec = load_template(report.template)
        section_titles = {section["key"]: section["title"] for section in spec.get("sections", [])}
        task_records: dict[str, dict[str, Any]] = {}
        results: dict[str, Any] = {}
        for ref in report.task_refs:
            record = history_manager.get(ref.task_id)
            if record is not None:
                task_records[ref.task_id] = record
                result = history_manager.load_result(ref.task_id)
                if result is not None:
                    results[ref.task_id] = result
        lines = [
            f"# {report.title}",
            "",
            f"- 项目：{report.project or '-'}",
            f"- 作者：{report.author or '-'}",
            f"- 更新：{report.updated_at[:16]}",
            f"- 模板：{report.template}",
        ]
        if report.description:
            lines.extend(["", report.description])
        lines.extend(["", "## Executive Summary", "", self._summary(task_records, results)])
        for key, title in section_titles.items():
            notes = report.sections.get(key, "")
            section_refs = [ref for ref in report.task_refs if ref.section == key]
            lines.extend(["", f"## {title}"])
            if notes:
                lines.extend(["", notes])
            for ref in section_refs:
                record = task_records.get(ref.task_id)
                if record is None:
                    lines.append(f"- [缺失引用] {ref.task_id}")
                    continue
                lines.append(
                    f"- `{record['tool_id']}`：{record.get('summary') or record['status']}"
                )
        lines.extend(["", "## Findings", ""])
        lines.extend(self._findings(results))
        if report.conclusion:
            lines.extend(["", "## Conclusion", "", report.conclusion])
        lines.extend(
            [
                "",
                "---",
                "",
                "> 本报告由 Binary Alchemist Cyber Toolkit 自动生成；Finding 为工具分析"
                "结果，不自动等同于实际漏洞。",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _summary(records: dict[str, dict[str, Any]], results: dict[str, Any]) -> str:
        statuses = Counter(record["status"] for record in records.values())
        findings: Counter[str] = Counter()
        for result in results.values():
            for finding in result.findings:
                findings[finding.severity.value] += 1
        lines = [
            f"本报告包含 {len(records)} 个分析任务："
            f"成功 {statuses.get('COMPLETED', 0)}，失败 {statuses.get('FAILED', 0)}，"
            f"取消 {statuses.get('CANCELLED', 0)}。",
        ]
        severity_line = "Finding：" + "，".join(
            f"{severity} {findings.get(severity, 0)}"
            for severity in SEVERITY_ORDER
            if findings.get(severity)
        )
        lines.append(severity_line or "Finding：无")
        return "\n".join(lines)

    @staticmethod
    def _findings(results: dict[str, Any]) -> list[str]:
        findings = [(finding, result) for result in results.values() for finding in result.findings]
        findings.sort(key=lambda item: SEVERITY_ORDER.index(item[0].severity.value))
        if not findings:
            return ["未发现 Finding。"]
        lines: list[str] = []
        for finding, _result in findings:
            lines.append(f"### [{finding.severity.value}] {finding.title}")
            if finding.description:
                lines.append(f"检测结果：{finding.description}")
            if finding.evidence:
                lines.append(f"- 证据：{finding.evidence}")
            if finding.recommendation:
                lines.append(f"- 建议：{finding.recommendation}")
            lines.append("")
        return lines


class HTMLReportExporter:
    """Reserved interface for a future local HTML exporter."""


class PDFReportExporter:
    """Reserved interface for a future local PDF exporter."""
