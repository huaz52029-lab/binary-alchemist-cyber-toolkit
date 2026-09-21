"""Flag extraction tool."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.ctf.flag_tools import FlagToolsTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-flag",
        tool_id="ctf.flag_tools",
        logger=logging.getLogger("tests.flag"),
        cancel_event=threading.Event(),
    )


def test_extract_default_formats() -> None:
    result = FlagToolsTool().run(
        {"text": "flag{test} ctf{other} BA{custom} nothing"},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    flags = {row["flag"] for row in result.data}
    assert flags == {"flag{test}", "ctf{other}", "BA{custom}"}
    assert any(finding.title == "Flag 均为候选" for finding in result.findings)


def test_custom_pattern() -> None:
    result = FlagToolsTool().run(
        {"text": "X CTF{t}, Y flag{t}", "custom_pattern": r"CTF\{[^}]+\}"},
        _context(),
    )
    assert any(row["flag"] == "CTF{t}" for row in result.data)


def test_no_flag() -> None:
    result = FlagToolsTool().run({"text": "nothing here"}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert result.data == []
    assert result.summary == "未发现 Flag 候选。"
