"""Hash calculator: known vectors, file hashing, comparison and errors."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import pytest

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.crypto.hash import HashTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-hash",
        tool_id="crypto.hash",
        logger=logging.getLogger("tests.hash"),
        cancel_event=threading.Event(),
    )


@pytest.mark.parametrize(
    ("algorithm", "text", "expected"),
    [
        ("MD5", "", "d41d8cd98f00b204e9800998ecf8427e"),
        ("MD5", "hello", "5d41402abc4b2a76b9719d911017c592"),
        ("SHA1", "hello", "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"),
        (
            "SHA256",
            "",
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        ),
        (
            "SHA256",
            "你好",
            "670d9743542cae3ea7ebe36af56bd53648b0a1126162e78d81a32934a711302e",
        ),
        (
            "SHA512",
            "hello",
            "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca72"
            "323c3d99ba5c11d7c7acc6e14b8c5da0c4663475c2e5c3adef46f73bcdec043",
        ),
    ],
)
def test_known_hash_vectors(algorithm: str, text: str, expected: str) -> None:
    result = HashTool().run(
        {"mode": "text", "input": text, "algorithm": algorithm},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["hash"] == expected
    assert result.data[0]["algorithm"] == algorithm


def test_hash_case_sensitivity() -> None:
    lower = HashTool().run({"mode": "text", "input": "hello", "algorithm": "MD5"}, _context())
    upper = HashTool().run({"mode": "text", "input": "Hello", "algorithm": "MD5"}, _context())
    assert lower.data[0]["hash"] != upper.data[0]["hash"]


def test_file_hash_matches_text_hash(tmp_path: Path) -> None:
    content = b"chunked file content " * 5000
    path = tmp_path / "data.bin"
    path.write_bytes(content)
    result = HashTool().run(
        {"mode": "file", "file_path": str(path), "algorithm": "SHA256"},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert (
        result.data[0]["hash"]
        == HashTool()
        .run(
            {"mode": "text", "input": content.decode("utf-8"), "algorithm": "SHA256"},
            _context(),
        )
        .data[0]["hash"]
    )
    assert result.data[0]["file_name"] == "data.bin"
    assert result.data[0]["file_size"] == len(content)


def test_file_hash_missing_file(tmp_path: Path) -> None:
    result = HashTool().run(
        {"mode": "file", "file_path": str(tmp_path / "nope.bin"), "algorithm": "MD5"},
        _context(),
    )
    assert result.status is ResultStatus.FAILED
    assert result.summary == "文件不存在。"


def test_compare_match_and_mismatch() -> None:
    tool = HashTool()
    match = tool.run(
        {
            "mode": "text",
            "input": "hello",
            "algorithm": "MD5",
            "compare_hash": "5D41402ABC4B2A76B9719D911017C592",
        },
        _context(),
    )
    assert match.data[0]["compare_result"] == "MATCH"
    assert match.findings[0].title == "Hash 一致"
    mismatch = tool.run(
        {
            "mode": "text",
            "input": "hello",
            "algorithm": "MD5",
            "compare_hash": "d41d8cd98f00b204e9800998ecf8427e",
        },
        _context(),
    )
    assert mismatch.data[0]["compare_result"] == "NOT MATCH"
    assert "不代表文件不安全" in mismatch.findings[0].description


def test_unknown_algorithm_fails() -> None:
    result = HashTool().run(
        {"mode": "text", "input": "x", "algorithm": "CRC32"},
        _context(),
    )
    assert result.status is ResultStatus.FAILED
    assert result.summary == "不支持的哈希算法。"
