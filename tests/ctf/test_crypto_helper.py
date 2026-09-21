"""Crypto helper orchestration."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from core.tool_registry import ToolRegistry
from modules import register_builtin_tools
from modules.ctf.crypto_helper import CryptoHelperTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-ch",
        tool_id="ctf.crypto_helper",
        logger=logging.getLogger("tests.ch"),
        cancel_event=threading.Event(),
    )


def test_crypto_helper_hash() -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    result = CryptoHelperTool(registry).run(
        {"mode": "hash", "input": "hello", "algorithm": "MD5"},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["hash"] == "5d41402abc4b2a76b9719d911017c592"
    assert result.metadata["forwarded_by"] == "ctf.crypto_helper"


def test_crypto_helper_base64() -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    result = CryptoHelperTool(registry).run(
        {"mode": "base64", "input": "hello", "operation": "encode"},
        _context(),
    )
    assert result.data[0]["output"] == "aGVsbG8="


def test_crypto_helper_rsa() -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    result = CryptoHelperTool(registry).run(
        {"mode": "rsa", "n": "3233", "e": "17", "d": "2753", "p": "61", "q": "53"},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["phi"] == 3120
