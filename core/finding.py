"""Structured, calibrated analysis findings.

A finding is a fact, a heuristic observation or a risk note - never a fabricated
verdict. Callers must set :attr:`Finding.kind` explicitly so the UI can separate
observed facts from interpretations.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    """Unified risk levels, from informational to critical."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        """Numeric ordering value, useful for sorting and thresholding."""
        return _SEVERITY_RANK[self]


class FindingKind(StrEnum):
    """Whether a finding is an observed fact, a heuristic or a risk note."""

    FACT = "FACT"
    HEURISTIC = "HEURISTIC"
    RISK = "RISK"


_SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class Finding(BaseModel):
    """A single, immutable analysis finding."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1, max_length=200)
    severity: Severity = Severity.INFO
    kind: FindingKind = FindingKind.HEURISTIC
    description: str = ""
    evidence: str = ""
    recommendation: str | None = None
    source: str = ""
