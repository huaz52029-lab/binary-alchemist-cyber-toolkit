"""Regex tool: templates, groups, replace and errors."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.ctf.regex import RegexTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-regex",
        tool_id="ctf.regex",
        logger=logging.getLogger("tests.regex"),
        cancel_event=threading.Event(),
    )


def test_findall_ipv4() -> None:
    result = RegexTool().run(
        {
            "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "text": "a 192.168.1.1 b 10.0.0.1",
            "mode": "findall",
        },
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert [row["match"] for row in result.data] == ["192.168.1.1", "10.0.0.1"]


def test_template_flag() -> None:
    result = RegexTool().run(
        {"template": "flag", "text": "xx flag{abc} yy", "mode": "findall"},
        _context(),
    )
    assert result.data[0]["match"] == "flag{abc}"


def test_groups() -> None:
    result = RegexTool().run(
        {"pattern": r"(\w+)@(\w+\.\w+)", "text": "a@b.com", "mode": "groups"},
        _context(),
    )
    assert [row["match"] for row in result.data] == ["a@b.com", "a", "b.com"]


def test_replace() -> None:
    result = RegexTool().run(
        {"pattern": r"\d+", "text": "a1b2", "mode": "replace", "replacement": "X"},
        _context(),
    )
    assert result.data[0]["value"] == "aXbX"


def test_invalid_regex_fails() -> None:
    result = RegexTool().run(
        {"pattern": "(unclosed", "text": "x", "mode": "findall"},
        _context(),
    )
    assert result.status is ResultStatus.FAILED
    assert "正则表达式无效" in result.summary


def test_complexity_hint() -> None:
    result = RegexTool().run(
        {"pattern": r"(a+)+", "text": "a" * 100, "mode": "findall"},
        _context(),
    )
    assert any(finding.title == "表达式可能存在较高计算复杂度" for finding in result.findings)
