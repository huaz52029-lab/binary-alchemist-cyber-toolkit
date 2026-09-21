"""Workspace data models (Pydantic)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


class ChallengeMetadata(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=200)
    category: str = "misc"
    tags: list[str] = Field(default_factory=list)
    notes_summary: str = ""
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)

    def model_dump_json_meta(self) -> str:
        import json

        return json.dumps(self.model_dump(mode="json"), ensure_ascii=False, indent=2)


class PipelineStep(BaseModel):
    tool: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class PipelineDefinition(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    pipeline_version: int = 1
    steps: list[PipelineStep] = Field(min_length=1)
