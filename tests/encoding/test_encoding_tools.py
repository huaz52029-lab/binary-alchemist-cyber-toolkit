"""Tool-level behavior for the ten encoding tools."""

from __future__ import annotations

import logging
import threading

import pytest

from core.result import ResultStatus
from core.task import ExecutionContext
from core.tool_registry import ToolRegistry
from modules import register_builtin_tools


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-enc",
        tool_id="encoding.base64",
        logger=logging.getLogger("tests.encoding"),
        cancel_event=threading.Event(),
    )


@pytest.mark.parametrize(
    ("tool_id", "encode_input", "encoded"),
    [
        ("encoding.base64", "Hello", "SGVsbG8="),
        ("encoding.base32", "Hello", "JBSWY3DP"),
        ("encoding.base58", "Hello", "9Ajdvzr"),
        ("encoding.hex", "Hello", "48656c6c6f"),
        ("encoding.binary", "A", "01000001"),
        ("encoding.url", "hello world", "hello%20world"),
        ("encoding.unicode", "你好", "\\u4f60\\u597d"),
        ("encoding.rot13", "hello", "uryyb"),
        ("encoding.rot47", "!", "P"),
        ("encoding.html_entity", "<", "&lt;"),
    ],
)
def test_encoding_tools_encode_and_decode(
    tool_id: str,
    encode_input: str,
    encoded: str,
) -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    tool = registry.get(tool_id)
    assert tool is not None
    encoded_result = tool.run({"input": encode_input, "operation": "encode"}, _context())
    assert encoded_result.status is ResultStatus.SUCCESS
    assert encoded_result.data[0]["output"] == encoded
    decoded_result = tool.run({"input": encoded, "operation": "decode"}, _context())
    assert decoded_result.status is ResultStatus.SUCCESS
    assert decoded_result.data[0]["output"] == encode_input


def test_rot13_transform_operation() -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    tool = registry.get("encoding.rot13")
    assert tool is not None
    result = tool.run({"input": "hello", "operation": "transform"}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["output"] == "uryyb"


def test_encoding_error_is_failed_result() -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    tool = registry.get("encoding.base64")
    assert tool is not None
    result = tool.run({"input": "!!!", "operation": "decode"}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == "输入不是有效的Base64数据。"


def test_all_encoding_ids_registered() -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    ids = {definition.id for definition in registry.list_tools()}
    assert {
        "encoding.base64",
        "encoding.base32",
        "encoding.base58",
        "encoding.hex",
        "encoding.binary",
        "encoding.url",
        "encoding.unicode",
        "encoding.rot13",
        "encoding.rot47",
        "encoding.html_entity",
    } <= ids


def test_encoding_page_hint() -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    assert registry.definition_of("encoding.base64").page == "encoding"  # type: ignore[union-attr]
