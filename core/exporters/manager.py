"""ExportManager: the single entry point for result export."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from core.exceptions import ExportError
from core.result import ToolResult


class ResultExporter(Protocol):
    """Structural contract implemented by every format exporter."""

    name: str
    extensions: tuple[str, ...]

    def export(self, result: ToolResult, path: Path) -> Path: ...

    def to_string(self, result: ToolResult) -> str: ...


class ExportManager:
    """Routes ToolResult exports to the right format, selected by name or suffix."""

    def __init__(self) -> None:
        self._exporters: dict[str, ResultExporter] = {}

    @classmethod
    def with_defaults(cls) -> ExportManager:
        """Build a manager preloaded with the JSON / CSV / TXT exporters."""
        from core.exporters.csv_exporter import CsvExporter
        from core.exporters.json_exporter import JsonExporter
        from core.exporters.txt_exporter import TxtExporter

        manager = cls()
        manager.register(JsonExporter())
        manager.register(CsvExporter())
        manager.register(TxtExporter())
        return manager

    def register(self, exporter: ResultExporter) -> None:
        self._exporters[exporter.name] = exporter

    def formats(self) -> tuple[str, ...]:
        return tuple(self._exporters)

    def to_string(self, result: ToolResult, fmt: str) -> str:
        return self._resolve(fmt).to_string(result)

    def export(self, result: ToolResult, path: Path, *, fmt: str | None = None) -> Path:
        """Write *result* to *path*; the format comes from *fmt* or the suffix."""
        resolved_format = fmt or path.suffix.lstrip(".").lower()
        if not resolved_format:
            raise ExportError(
                "cannot determine export format from an empty path suffix",
                user_message="无法确定导出格式，请提供带扩展名的文件名。",
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        return self._resolve(resolved_format).export(result, path)

    def _resolve(self, fmt: str) -> ResultExporter:
        exporter = self._exporters.get(fmt.lower())
        if exporter is None:
            raise ExportError(
                f"unsupported export format: {fmt}",
                user_message=f"不支持的导出格式：{fmt}",
            )
        return exporter
