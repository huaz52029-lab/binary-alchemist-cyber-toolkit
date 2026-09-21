"""CSV export of the tabular ``data`` section of a ToolResult."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from core.result import ToolResult


class CsvExporter:
    """Flattens ``result.data`` rows into a CSV document.

    Columns are the union of all row keys in first-seen order. An empty ``data``
    section yields an empty document; use JSON/TXT for non-tabular results.
    """

    name: str = "csv"
    extensions: tuple[str, ...] = ("csv",)

    def to_string(self, result: ToolResult) -> str:
        rows = result.data
        if not rows:
            return ""
        fieldnames: list[str] = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return buffer.getvalue()

    def export(self, result: ToolResult, path: Path) -> Path:
        # utf-8-sig keeps Chinese text readable in Excel.
        path.write_text(self.to_string(result), encoding="utf-8-sig")
        return path
