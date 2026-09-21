"""JSON export of a ToolResult."""

from __future__ import annotations

import json
from pathlib import Path

from core.result import ToolResult


class JsonExporter:
    """Serializes the full unified result as pretty JSON."""

    name: str = "json"
    extensions: tuple[str, ...] = ("json",)

    def to_string(self, result: ToolResult) -> str:
        return json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2)

    def export(self, result: ToolResult, path: Path) -> Path:
        path.write_text(self.to_string(result) + "\n", encoding="utf-8")
        return path
