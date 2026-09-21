"""Modular math operations."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.ctf.mod_math import ModMathTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-mod",
        tool_id="ctf.mod_math",
        logger=logging.getLogger("tests.mod"),
        cancel_event=threading.Event(),
    )


def test_mod_operations() -> None:
    tool = ModMathTool()
    assert (
        tool.run({"operation": "gcd", "a": "48", "b": "18", "n": "1"}, _context()).data[0]["result"]
        == "6"
    )
    assert (
        tool.run({"operation": "powmod", "a": "2", "b": "10", "n": "1000"}, _context()).data[0][
            "result"
        ]
        == "24"
    )
    assert (
        tool.run({"operation": "inverse", "a": "3", "b": "0", "n": "11"}, _context()).data[0][
            "result"
        ]
        == "4"
    )
    assert (
        tool.run({"operation": "lcm", "a": "4", "b": "6", "n": "1"}, _context()).data[0]["result"]
        == "12"
    )


def test_mod_invalid_inputs() -> None:
    result = ModMathTool().run({"operation": "mod", "a": "x", "b": "1", "n": "2"}, _context())
    assert result.status is ResultStatus.FAILED
    zero_mod = ModMathTool().run({"operation": "mod", "a": "1", "b": "0", "n": "0"}, _context())
    assert zero_mod.status is ResultStatus.FAILED


def test_inverse_not_coprime() -> None:
    result = ModMathTool().run({"operation": "inverse", "a": "2", "b": "0", "n": "4"}, _context())
    assert result.status is ResultStatus.FAILED
    assert "不互质" in result.summary
