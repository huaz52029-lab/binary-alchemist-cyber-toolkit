"""Unified result model shared by every tool.

All tools return a :class:`ToolResult` with the same shape so that the UI, exporters
and report center can treat every module uniformly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from core.exceptions import to_user_message
from core.finding import Finding


class ResultStatus(StrEnum):
    """Lifecycle outcome of a tool execution."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class LogEntry(BaseModel):
    """A single structured log record attached to a result."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    level: str = "INFO"
    message: str


class ToolResult(BaseModel):
    """Unified output of a tool execution."""

    status: ResultStatus
    summary: str = ""
    data: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    logs: list[LogEntry] = Field(default_factory=list)
    duration: float | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def success(cls, summary: str, **extra: Any) -> ToolResult:
        """Build a successful result."""
        return cls(status=ResultStatus.SUCCESS, summary=summary, **extra)

    @classmethod
    def partial(cls, summary: str, **extra: Any) -> ToolResult:
        """Build a partially successful result (some items failed)."""
        return cls(status=ResultStatus.PARTIAL, summary=summary, **extra)

    @classmethod
    def failure(cls, summary: str, **extra: Any) -> ToolResult:
        """Build a failed result."""
        return cls(status=ResultStatus.FAILED, summary=summary, **extra)

    @classmethod
    def from_exception(
        cls,
        exc: BaseException,
        *,
        cancelled: bool = False,
        timed_out: bool = False,
    ) -> ToolResult:
        """Build a result from an exception with a user-friendly summary."""
        if cancelled:
            status = ResultStatus.CANCELLED
        elif timed_out:
            status = ResultStatus.TIMEOUT
        else:
            status = ResultStatus.FAILED
        return cls(status=status, summary=to_user_message(exc))

    @property
    def is_ok(self) -> bool:
        """Whether the run produced at least a partial result."""
        return self.status in (ResultStatus.SUCCESS, ResultStatus.PARTIAL)

    def add_finding(self, finding: Finding) -> None:
        """Append a finding, keeping the unified shape intact."""
        self.findings.append(finding)

    def add_log(self, level: str, message: str) -> None:
        """Append a structured log record."""
        self.logs.append(LogEntry(level=level, message=message))
