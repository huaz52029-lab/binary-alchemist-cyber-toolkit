"""Auto Decode heuristic candidates."""

from __future__ import annotations

import json
import logging
import threading
import time

from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.crypto.base64url import base64url_encode
from modules.ctf.auto_decode import AutoDecodeTool, decode_candidates


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-auto",
        tool_id="ctf.auto_decode",
        logger=logging.getLogger("tests.auto"),
        cancel_event=threading.Event(),
    )


def _jwt_token() -> str:
    header = base64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8"))
    payload = base64url_encode(
        json.dumps({"sub": "ctf", "exp": int(time.time()) + 3600}).encode("utf-8")
    )
    return f"{header}.{payload}.sig"


def test_base64_candidate_ranked_first() -> None:
    candidates = decode_candidates("SGVsbG8=")
    assert candidates
    assert candidates[0].name == "Base64"
    assert candidates[0].level == "High"
    assert candidates[0].decoded == "Hello"


def test_hex_candidate_ranked_first() -> None:
    candidates = decode_candidates("68656c6c6f")
    assert candidates
    assert candidates[0].name == "Hex"
    assert candidates[0].decoded == "hello"


def test_unpadded_base64_recognized() -> None:
    candidates = decode_candidates("aGVsbG8=")
    assert any(candidate.name == "Base64" for candidate in candidates)


def test_ambiguous_input_has_no_high_confidence() -> None:
    candidates = decode_candidates("123456")
    assert all(candidate.level != "High" for candidate in candidates)


def test_jwt_candidate() -> None:
    candidates = decode_candidates(_jwt_token())
    top = candidates[0]
    assert top.name == "JWT"
    assert "Payload" in top.decoded
    assert top.level == "High"


def test_unicode_candidate() -> None:
    candidates = decode_candidates("\\u4f60\\u597d")
    assert any(
        candidate.name == "Unicode" and candidate.decoded == "你好" for candidate in candidates
    )


def test_tool_runs_and_returns_rows() -> None:
    result = AutoDecodeTool().run({"input": "SGVsbG8="}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["encoding"] == "Base64"
    assert result.data[0]["confidence"] == "High"
    assert result.findings[0].kind.value == "HEURISTIC"
    labels = [column["label"] for column in result.metadata["display"]["table"]["columns"]]
    assert labels == ["候选编码", "置信度", "解码结果", "说明"]


def test_tool_empty_input_fails() -> None:
    result = AutoDecodeTool().run({"input": "   "}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == "请输入要分析的文本。"
