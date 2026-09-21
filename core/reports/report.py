"""Report data models and bundled templates."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.paths import app_root


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return f"report_{uuid.uuid4().hex[:12]}"


class ReportTaskRef(BaseModel):
    task_id: str
    section: str = "Findings"
    sort_order: int = 0


class Report(BaseModel):
    """A user-authored report referencing tasks in the history."""

    model_config = ConfigDict(extra="ignore")

    report_id: str = Field(default_factory=_new_id)
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    author: str = ""
    project: str = ""
    tags: list[str] = Field(default_factory=list)
    template: str = "basic"
    sections: dict[str, str] = Field(default_factory=dict)  # section key -> notes
    conclusion: str = ""
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)
    revision: int = 1
    task_refs: list[ReportTaskRef] = Field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = _utcnow()
        self.revision += 1


# Runtime-rooted so the bundled templates resolve both from a source checkout
# and from a PyInstaller onedir layout (resources live next to the executable).
TEMPLATE_DIR = app_root() / "configs" / "report_templates"


def load_template(name: str) -> dict[str, Any]:
    """Load a report template (section structure) from JSON."""
    path = TEMPLATE_DIR / f"{name}.json"
    if not path.is_file():
        return {"name": name, "sections": [{"key": "findings", "title": "Findings"}]}
    try:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return payload
    except (OSError, json.JSONDecodeError):
        return {"name": name, "sections": [{"key": "findings", "title": "Findings"}]}
