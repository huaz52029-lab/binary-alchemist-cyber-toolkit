"""Data transform conversions."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.ctf.data_transform import DataTransformTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-dt",
        tool_id="ctf.data_transform",
        logger=logging.getLogger("tests.dt"),
        cancel_event=threading.Event(),
    )


def test_text_to_hex_to_integer() -> None:
    tool = DataTransformTool()
    hex_result = tool.run({"input": "Hi", "source": "text", "target": "hex"}, _context())
    assert hex_result.data[0]["result"] == "4869"
    int_result = tool.run({"input": "4869", "source": "hex", "target": "integer"}, _context())
    assert int_result.data[0]["result"] == str(int.from_bytes(b"Hi", "big"))
    back = tool.run(
        {"input": int_result.data[0]["result"], "source": "integer", "target": "text"}, _context()
    )
    assert back.data[0]["result"] == "Hi"


def test_endianness() -> None:
    tool = DataTransformTool()
    big = tool.run(
        {"input": "1", "source": "integer", "target": "hex", "endian": "big"}, _context()
    )
    little = tool.run(
        {"input": "1", "source": "integer", "target": "hex", "endian": "little"}, _context()
    )
    assert big.data[0]["result"] == "01"
    assert little.data[0]["result"] == "01"
    bigger = tool.run(
        {"input": "258", "source": "integer", "target": "hex", "endian": "big"}, _context()
    )
    little_bigger = tool.run(
        {"input": "258", "source": "integer", "target": "hex", "endian": "little"},
        _context(),
    )
    assert bigger.data[0]["result"] == "0102"
    assert little_bigger.data[0]["result"] == "0201"


def test_invalid_inputs() -> None:
    tool = DataTransformTool()
    bad_hex = tool.run({"input": "zz", "source": "hex", "target": "text"}, _context())
    assert bad_hex.status is ResultStatus.FAILED
    bad_text = tool.run({"input": "ffff", "source": "hex", "target": "text"}, _context())
    assert bad_text.status is ResultStatus.FAILED
    assert "UTF-8" in bad_text.summary
