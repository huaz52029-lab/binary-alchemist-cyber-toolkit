"""Shared fixtures for the core test suite."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from core.finding import Finding, FindingKind, Severity
from core.result import LogEntry, ResultStatus, ToolResult
from core.task import ExecutionContext
from core.tool_definition import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolParameters,
)


@pytest.fixture
def tmp_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated runtime home, also exported as CYBERTOOLKIT_HOME."""
    monkeypatch.setenv("CYBERTOOLKIT_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def sample_finding() -> Finding:
    return Finding(
        title="示例发现",
        severity=Severity.MEDIUM,
        kind=FindingKind.HEURISTIC,
        description="启发式判断示例",
        evidence="evidence: value",
        recommendation="人工复核后处置",
        source="system.dummy",
    )


@pytest.fixture
def sample_result(sample_finding: Finding) -> ToolResult:
    return ToolResult(
        status=ResultStatus.SUCCESS,
        summary="发现 2 条记录",
        data=[
            {"host": "127.0.0.1", "port": 80},
            {"host": "127.0.0.1", "port": 443},
        ],
        findings=[sample_finding],
        logs=[LogEntry(level="INFO", message="ok")],
        duration=0.12,
        metadata={"tool_id": "system.dummy"},
    )


class DummyTool(BaseTool):
    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="system.dummy",
        name="Dummy Tool",
        category=ToolCategory.SYSTEM,
        description="test tool",
        version="1.0.0",
        parameters=[ToolParameter(name="input", label="输入")],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        context.info("dummy running")
        value = params.get("value", "")
        return context.make_result(ResultStatus.SUCCESS, f"dummy ok: {value}")


@pytest.fixture
def dummy_tool() -> DummyTool:
    return DummyTool()
