"""CSV export of the tabular ``data`` section of a ToolResult.

Values are redacted with the unified sanitizer before writing, and cells that
look like spreadsheet formulas are neutralized to prevent CSV formula injection
when the file is opened in Excel.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from core.history.sanitizer import sanitize_json
from core.result import ToolResult

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _is_number_literal(value: str) -> bool:
    """Return whether *value* is a plain number, which Excel stores as data."""
    try:
        float(value)
    except ValueError:
        return False
    return True


def guard_cell(value: Any) -> Any:
    """Neutralize formula-like text cells; non-text values pass through."""
    if not isinstance(value, str):
        return value
    stripped = value.lstrip()
    if not stripped or stripped[0] not in _FORMULA_PREFIXES:
        return value
    if stripped[0] in ("-", "+") and _is_number_literal(stripped):
        return value
    return "'" + value


class CsvExporter:
    """Flattens ``result.data`` rows into a CSV document.

    Columns are the union of all row keys in first-seen order. An empty ``data``
    section yields an empty document; use JSON/TXT for non-tabular results.
    """

    name: str = "csv"
    extensions: tuple[str, ...] = ("csv",)

    def to_string(self, result: ToolResult) -> str:
        rows = sanitize_json(result.data)
        if not rows:
            return ""
        fieldnames: list[str] = []
        for row in rows:
            for key in row:
                safe_key = str(guard_cell(key))
                if safe_key not in fieldnames:
                    fieldnames.append(safe_key)
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: guard_cell(value) for key, value in row.items()} for row in rows)
        return buffer.getvalue()

    def export(self, result: ToolResult, path: Path) -> Path:
        # utf-8-sig keeps Chinese text readable in Excel.
        path.write_text(self.to_string(result), encoding="utf-8-sig")
        return path
