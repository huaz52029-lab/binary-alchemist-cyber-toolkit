from __future__ import annotations

import json

from core.result import ResultStatus, ToolResult


def test_success_helper_fills_defaults() -> None:
    result = ToolResult.success("ok")
    assert result.status is ResultStatus.SUCCESS
    assert result.data == []
    assert result.findings == []


def test_from_exception_cancelled_and_timeout() -> None:
    cancelled = ToolResult.from_exception(RuntimeError("x"), cancelled=True)
    timed_out = ToolResult.from_exception(RuntimeError("x"), timed_out=True)
    assert cancelled.status is ResultStatus.CANCELLED
    assert timed_out.status is ResultStatus.TIMEOUT


def test_is_ok(sample_result: ToolResult) -> None:
    assert sample_result.is_ok
    assert not ToolResult.failure("bad").is_ok


def test_json_serialization_roundtrip(sample_result: ToolResult) -> None:
    payload = json.loads(sample_result.model_dump_json())
    assert payload["status"] == "SUCCESS"
    assert payload["findings"][0]["severity"] == "MEDIUM"
    assert payload["duration"] == 0.12
