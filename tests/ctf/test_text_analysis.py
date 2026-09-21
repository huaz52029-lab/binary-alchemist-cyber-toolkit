"""Text analysis statistics."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.ctf.text_analysis import TextAnalysisTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-txt",
        tool_id="ctf.text_analysis",
        logger=logging.getLogger("tests.txt"),
        cancel_event=threading.Event(),
    )


def test_text_analysis_stats() -> None:
    result = TextAnalysisTool().run({"text": "hello world\n42!!", "top_n": 10}, _context())
    assert result.status is ResultStatus.SUCCESS
    rows = {(row["section"], row["item"]): row["value"] for row in result.data}
    assert rows[("统计", "字符数")] == "16"
    assert rows[("统计", "行数")] == "2"
    assert rows[("统计", "数字数")] == "2"
    assert rows[("编码", "候选编码")] == "ASCII"
    assert any(section == "频率" for section, _item in rows)


def test_text_analysis_chinese() -> None:
    result = TextAnalysisTool().run({"text": "你好世界", "top_n": 10}, _context())
    rows = {(row["section"], row["item"]): row["value"] for row in result.data}
    assert rows[("编码", "候选编码")].startswith("UTF-8")
