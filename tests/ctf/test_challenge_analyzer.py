"""Challenge analyzer classifications and recommendations."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.ctf.challenge_analyzer import ChallengeAnalyzerTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-cha",
        tool_id="ctf.challenge_analyzer",
        logger=logging.getLogger("tests.cha"),
        cancel_event=threading.Event(),
    )


def _values(result: object) -> list[str]:
    return [row["value"] for row in result.data]  # type: ignore[index]


def test_rsa_parameters_recommend_rsa_helper() -> None:
    result = ChallengeAnalyzerTool().run(
        {"text": "n = 3233\ne = 65537\np = 61\nq = 53"},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    values = [row["item"] for row in result.data]
    assert any("RSA 辅助" in item for item in values)


def test_jwt_recommends_jwt_tool() -> None:
    token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig"
    result = ChallengeAnalyzerTool().run({"text": token}, _context())
    assert any("JWT 解析器" in row["item"] for row in result.data)


def test_pe_file_recommends_file_analysis(tmp_path: Path) -> None:
    path = tmp_path / "sample.exe"
    path.write_bytes(b"MZ\x90\x00" + b"\x00" * 64)
    result = ChallengeAnalyzerTool().run({"file_path": str(path)}, _context())
    assert any("PE 分析" in row["item"] for row in result.data)


def test_unknown_text_low_confidence() -> None:
    result = ChallengeAnalyzerTool().run({"text": "just some plain text"}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert any(finding.title == "分类为候选类型" for finding in result.findings)
