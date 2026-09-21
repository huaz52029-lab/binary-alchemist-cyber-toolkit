from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.finding import Finding, FindingKind, Severity


def test_severity_rank_ordering() -> None:
    levels = list(Severity)
    assert levels == sorted(levels, key=lambda severity: severity.rank)


def test_finding_defaults() -> None:
    finding = Finding(title="t")
    assert finding.kind is FindingKind.HEURISTIC
    assert finding.severity is Severity.INFO


def test_finding_is_immutable(sample_finding: Finding) -> None:
    with pytest.raises(ValidationError):
        sample_finding.title = "changed"
