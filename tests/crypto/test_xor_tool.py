"""XOR helpers and tool modes."""

from __future__ import annotations

import logging
import threading

import pytest

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.crypto.xor import XorTool, hex_to_bytes, xor_repeating, xor_single


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-xor",
        tool_id="crypto.xor",
        logger=logging.getLogger("tests.xor"),
        cancel_event=threading.Event(),
    )


def test_xor_single_byte() -> None:
    assert xor_single(bytes([0x41]), 0x20) == bytes([0x61])  # 0x41 ^ 0x20 -> 'a'


def test_single_mode_via_tool() -> None:
    result = XorTool().run(
        {"mode": "single", "input": "41", "key_byte": 32},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["output_hex"] == "61"


def test_repeating_key_roundtrip() -> None:
    plaintext = b"attack at dawn"
    cipher = xor_repeating(plaintext, b"key")
    assert cipher != plaintext
    assert xor_repeating(cipher, b"key") == plaintext


def test_repeating_mode_via_tool() -> None:
    data = xor_repeating(b"hello", b"ab").hex()
    result = XorTool().run(
        {"mode": "repeating", "input": data, "key": "ab"},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["output_hex"] == b"hello".hex()


def test_hex_xor_equal_length() -> None:
    result = XorTool().run(
        {"mode": "hex_xor", "input": "48656c6c6f", "input_b": "0102030405"},
        _context(),
    )
    assert result.data[0]["output_hex"] == "49676f686a"


def test_hex_xor_unequal_length_fails() -> None:
    result = XorTool().run(
        {"mode": "hex_xor", "input": "4865", "input_b": "010203"},
        _context(),
    )
    assert result.status is ResultStatus.FAILED
    assert result.summary == "两个Hex输入长度不同。"


@pytest.mark.parametrize("value", ["zz", "486", "abc"])
def test_invalid_hex_input_fails(value: str) -> None:
    result = XorTool().run({"mode": "single", "input": value, "key_byte": 1}, _context())
    assert result.status is ResultStatus.FAILED
    assert "Hex" in result.summary


def test_empty_input_fails() -> None:
    result = XorTool().run({"mode": "brute", "input": "  "}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == "输入不能为空。"


def test_repeating_empty_key_fails() -> None:
    result = XorTool().run({"mode": "repeating", "input": "41", "key": ""}, _context())
    assert result.status is ResultStatus.FAILED
    assert "密钥" in result.summary


def test_brute_mode_scores_plaintext_first() -> None:
    cipher = xor_single(b"hello world", 0x41).hex()
    result = XorTool().run({"mode": "brute", "input": cipher}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert len(result.data) == 256
    assert result.data[0]["key_hex"] == "0x41"
    assert result.data[0]["preview"] == "hello world"
    assert result.findings[0].kind.value == "HEURISTIC"


def test_hex_to_bytes_whitespace() -> None:
    assert hex_to_bytes("48 65\n6c 6c 6f") == b"Hello"
