"""ReportManager: create, save, reference tasks and export reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.exceptions import ExportError
from core.reports.report import Report, ReportTaskRef, load_template
from core.reports.report_renderer import ReportRenderer
from core.reports.report_repository import ReportRepository


class ReportManager:
    """Application service between the report UI and the repository/renderer."""

    def __init__(
        self,
        repository: ReportRepository,
        history_manager: Any,
    ) -> None:
        self._repository = repository
        self._history = history_manager
        self._renderer = ReportRenderer()

    @property
    def repository(self) -> ReportRepository:
        """Read-only access to the underlying repository (for maintenance)."""
        return self._repository

    def create(
        self,
        title: str,
        *,
        description: str = "",
        author: str = "",
        project: str = "",
        tags: list[str] | None = None,
        template: str = "basic",
    ) -> Report:
        spec = load_template(template)
        sections = {section["key"]: "" for section in spec.get("sections", [])}
        report = Report(
            title=title,
            description=description,
            author=author,
            project=project,
            tags=tags or [],
            template=template,
            sections=sections,
        )
        self.save(report)
        return report

    def save(self, report: Report) -> Report:
        report.touch()
        self._repository.save(report)
        return report

    def get(self, report_id: str) -> Report | None:
        return self._repository.get(report_id)

    def list(self, search: str = "") -> tuple[list[Report], dict[str, int]]:
        return self._repository.list(search)

    def delete(self, report_id: str) -> None:
        self._repository.delete(report_id)

    def add_task(self, report_id: str, task_id: str, section: str = "Findings") -> Report | None:
        report = self._repository.get(report_id)
        if report is None:
            return None
        if any(ref.task_id == task_id for ref in report.task_refs):
            return report
        report.task_refs.append(
            ReportTaskRef(
                task_id=task_id,
                section=section,
                sort_order=len(report.task_refs),
            )
        )
        self.save(report)
        return report

    def remove_task(self, report_id: str, task_id: str) -> Report | None:
        report = self._repository.get(report_id)
        if report is None:
            return None
        report.task_refs = [ref for ref in report.task_refs if ref.task_id != task_id]
        self.save(report)
        return report

    def render_markdown(self, report_id: str) -> str | None:
        report = self._repository.get(report_id)
        if report is None:
            return None
        return self._renderer.render(report, self._history)

    def export(
        self,
        report_id: str,
        path: Path,
        *,
        fmt: str | None = None,
    ) -> Path:
        report = self._repository.get(report_id)
        if report is None:
            raise ExportError("report not found", user_message="报告不存在。")
        fmt = fmt or path.suffix.lstrip(".").lower()
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "json":
            path.write_text(
                json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        elif fmt in ("md", "txt"):
            path.write_text(self._renderer.render(report, self._history), encoding="utf-8")
        else:
            raise ExportError(
                f"unsupported report format: {fmt}", user_message=f"不支持的导出格式：{fmt}"
            )
        return path

    def close(self) -> None:
        self._repository.close()
