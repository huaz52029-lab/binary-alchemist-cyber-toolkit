"""MD5 reverse tool: verify / dictionary / brute-force modes and cancellation."""

from __future__ import annotations

import json
import logging
import threading
import time
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest

from core.exceptions import TaskCancelledError
from core.exporters import ExportManager
from core.result import ResultStatus
from core.task import ExecutionContext, TaskStatus
from core.task_manager import TaskManager
from infrastructure.crypto import md5_hexdigest
from modules import register_builtin_tools
from modules.crypto.md5_reverse import MD5ReverseCtfTool, MD5ReverseTool


def _context(
    on_progress: Any = None,
    event: threading.Event | None = None,
) -> ExecutionContext:
    return ExecutionContext(
        task_id="t-md5",
        tool_id="crypto.md5_reverse",
        logger=logging.getLogger("tests.md5"),
        cancel_event=event or threading.Event(),
        on_progress=on_progress,
    )


def test_verify_matched_and_unmatched() -> None:
    tool = MD5ReverseTool()
    matched = tool.run(
        {"mode": "verify", "target": md5_hexdigest("hello"), "candidate": "hello"},
        _context(),
    )
    assert matched.status is ResultStatus.SUCCESS
    assert matched.data[0]["matched"] == "是"
    assert "匹配 1/1" in matched.summary
    unmatched = tool.run(
        {"mode": "verify", "target": md5_hexdigest("hello"), "candidate": "world"},
        _context(),
    )
    assert unmatched.data[0]["matched"] == "否"
    assert "未匹配" in unmatched.summary


def test_verify_hash_is_case_insensitive_and_trimmed() -> None:
    result = MD5ReverseTool().run(
        {"mode": "verify", "target": " 5D41402ABC4B2A76B9719D911017C592 ", "candidate": "hello"},
        _context(),
    )
    assert result.data[0]["matched"] == "是"


def test_verify_empty_candidate() -> None:
    result = MD5ReverseTool().run(
        {"mode": "verify", "target": md5_hexdigest(""), "candidate": ""},
        _context(),
    )
    assert result.data[0]["matched"] == "是"


def test_verify_batch_hashes() -> None:
    tool = MD5ReverseTool()
    target = f"{md5_hexdigest('hello')}\n{md5_hexdigest('world')}"
    result = tool.run({"mode": "verify", "target": target, "candidate": "hello"}, _context())
    assert len(result.data) == 2
    assert [row["matched"] for row in result.data] == ["是", "否"]
    assert "匹配 1/2" in result.summary


def test_verify_invalid_hash_fails_gracefully() -> None:
    result = MD5ReverseTool().run(
        {"mode": "verify", "target": "12345", "candidate": "hello"},
        _context(),
    )
    assert result.status is ResultStatus.FAILED
    assert "无效的MD5 Hash" in result.summary


def test_dictionary_finds_match(tmp_path: Path) -> None:
    dictionary = tmp_path / "dict.txt"
    dictionary.write_text("123456\npassword\nhello\nadmin\ntest\n", encoding="utf-8")
    result = MD5ReverseTool().run(
        {
            "mode": "dictionary",
            "target": md5_hexdigest("hello"),
            "dictionary_path": str(dictionary),
        },
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["matched"] is True
    assert result.data[0]["plaintext"] == "hello"
    assert result.data[0]["attempts"] == 3
    assert "找到候选" in result.summary


def test_dictionary_not_found(tmp_path: Path) -> None:
    dictionary = tmp_path / "dict.txt"
    dictionary.write_text("123456\npassword\nadmin\ntest\n", encoding="utf-8")
    result = MD5ReverseTool().run(
        {
            "mode": "dictionary",
            "target": md5_hexdigest("hello"),
            "dictionary_path": str(dictionary),
        },
        _context(),
    )
    assert result.data[0]["matched"] is False
    assert result.data[0]["attempts"] == 4
    assert "仅代表当前搜索空间内未找到" in result.summary


def test_dictionary_preserves_spaces(tmp_path: Path) -> None:
    dictionary = tmp_path / "dict.txt"
    dictionary.write_text("hello\n world \n", encoding="utf-8")
    result = MD5ReverseTool().run(
        {
            "mode": "dictionary",
            "target": md5_hexdigest(" world "),
            "dictionary_path": str(dictionary),
        },
        _context(),
    )
    assert result.data[0]["matched"] is True
    assert result.data[0]["plaintext"] == " world "


def test_dictionary_missing_file(tmp_path: Path) -> None:
    result = MD5ReverseTool().run(
        {
            "mode": "dictionary",
            "target": md5_hexdigest("hello"),
            "dictionary_path": str(tmp_path / "nope.txt"),
        },
        _context(),
    )
    assert result.status is ResultStatus.FAILED
    assert result.summary == "字典文件不存在。"


def test_dictionary_invalid_utf8(tmp_path: Path) -> None:
    dictionary = tmp_path / "dict.bin"
    dictionary.write_bytes(b"123456\n\xff\xfe\x00\n")
    result = MD5ReverseTool().run(
        {
            "mode": "dictionary",
            "target": md5_hexdigest("hello"),
            "dictionary_path": str(dictionary),
        },
        _context(),
    )
    assert result.status is ResultStatus.FAILED
    assert "不是有效的UTF-8" in result.summary


def test_dictionary_reports_progress(tmp_path: Path) -> None:
    dictionary = tmp_path / "dict.txt"
    dictionary.write_text(
        "\n".join(f"candidate-{index}" for index in range(2000)) + "\n", encoding="utf-8"
    )
    progress: list[float | None] = []
    messages: list[str] = []

    def on_progress(value: float | None, message: str | None) -> None:
        progress.append(value)
        if message:
            messages.append(message)

    MD5ReverseTool().run(
        {
            "mode": "dictionary",
            "target": md5_hexdigest("not-in-dict"),
            "dictionary_path": str(dictionary),
        },
        _context(on_progress=on_progress),
    )
    assert progress[-1] == 100.0
    assert any("速度" in message for message in messages)
    known = [value for value in progress if value is not None]
    assert all(later >= earlier for earlier, later in pairwise(known))


def test_bruteforce_finds_match() -> None:
    result = MD5ReverseTool().run(
        {
            "mode": "bruteforce",
            "target": md5_hexdigest("cab"),
            "charset": "abc",
            "min_length": 1,
            "max_length": 3,
        },
        _context(),
    )
    assert result.data[0]["matched"] is True
    assert result.data[0]["plaintext"] == "cab"
    assert "找到候选" in result.summary


def test_bruteforce_not_found_exhausts_space() -> None:
    result = MD5ReverseTool().run(
        {
            "mode": "bruteforce",
            "target": md5_hexdigest("zzz"),
            "charset": "abc",
            "min_length": 1,
            "max_length": 2,
        },
        _context(),
    )
    assert result.data[0]["matched"] is False
    assert result.data[0]["attempts"] == 12  # 3 + 9
    assert "未在当前搜索空间中找到匹配候选" in result.summary


@pytest.mark.parametrize(
    "params",
    [
        {"mode": "bruteforce", "target": "d" * 32, "charset": "", "min_length": 1, "max_length": 3},
        {
            "mode": "bruteforce",
            "target": "d" * 32,
            "charset": "ab",
            "min_length": 3,
            "max_length": 2,
        },
        {
            "mode": "bruteforce",
            "target": "d" * 32,
            "charset": "ab",
            "min_length": 1,
            "max_length": 9,
        },
    ],
)
def test_bruteforce_invalid_parameters(params: dict[str, Any]) -> None:
    result = MD5ReverseTool().run(params, _context())
    assert result.status is ResultStatus.FAILED


def test_large_space_adds_heuristic_finding() -> None:
    result = MD5ReverseTool().run(
        {
            "mode": "bruteforce",
            "target": md5_hexdigest("not-found"),
            "charset": "abcdefghij",
            "min_length": 1,
            "max_length": 6,
        },
        _context(),
    )
    assert any(finding.title == "搜索空间较大" for finding in result.findings)


def test_cancellation_propagates() -> None:
    event = threading.Event()

    def on_progress(_value: float | None, _message: str | None) -> None:
        event.set()

    with pytest.raises(TaskCancelledError):
        MD5ReverseTool().run(
            {
                "mode": "bruteforce",
                "target": md5_hexdigest("hello"),
                "charset": "abcdefghijklmnopqrstuvwxyz",
                "min_length": 1,
                "max_length": 6,
            },
            _context(on_progress=on_progress, event=event),
        )


def test_task_manager_cancels_bruteforce() -> None:
    manager = TaskManager(max_workers=2)
    try:
        task_id = manager.submit_tool(
            MD5ReverseTool(),
            {
                "mode": "bruteforce",
                "target": md5_hexdigest("hello"),
                "charset": "abcdefghijklmnopqrstuvwxyz",
                "min_length": 1,
                "max_length": 6,
            },
        )
        time.sleep(0.15)
        manager.cancel(task_id)
        snapshot = manager.wait(task_id, timeout=10.0)
        assert snapshot.status is TaskStatus.CANCELLED
    finally:
        manager.shutdown(wait=True)


def test_result_exports_json_txt_csv(tmp_path: Path) -> None:
    result = MD5ReverseTool().run(
        {"mode": "verify", "target": md5_hexdigest("hello"), "candidate": "hello"},
        _context(),
    )
    manager = ExportManager.with_defaults()
    exported = manager.export(result, tmp_path / "md5.json")
    payload = json.loads(exported.read_text(encoding="utf-8"))
    assert payload["status"] == "SUCCESS"
    assert payload["data"][0]["candidate"] == "hello"
    assert "hello" in manager.to_string(result, "txt")
    assert "candidate" in manager.to_string(result, "csv")


def test_ctf_entry_reuses_single_implementation() -> None:
    from core.tool_registry import ToolRegistry

    registry = ToolRegistry()
    register_builtin_tools(registry)
    assert "crypto.md5_reverse" in registry
    assert "ctf.md5_reverse" in registry
    ctf_tool = registry.get("ctf.md5_reverse")
    assert ctf_tool is not None
    assert isinstance(ctf_tool, MD5ReverseTool)
    assert isinstance(ctf_tool, MD5ReverseCtfTool)
    result = ctf_tool.run(
        {"mode": "verify", "target": md5_hexdigest("hello"), "candidate": "hello"},
        _context(),
    )
    assert result.data[0]["matched"] == "是"
