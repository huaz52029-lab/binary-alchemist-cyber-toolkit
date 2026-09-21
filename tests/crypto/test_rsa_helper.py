"""RSA helper: parameter math, tool behavior and PEM parsing."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.crypto.rsa_helper import RsaHelperTool, RsaParameters, analyze_parameters


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-rsa",
        tool_id="crypto.rsa_helper",
        logger=logging.getLogger("tests.rsa"),
        cancel_event=threading.Event(),
    )


def test_classic_rsa_parameters() -> None:
    analysis = analyze_parameters(RsaParameters(n=3233, e=17, d=2753, p=61, q=53))
    assert analysis["n_matches_pq"] is True
    assert analysis["phi"] == 3120
    assert analysis["gcd_e_phi"] == 1
    assert analysis["d_computed"] == 2753
    assert analysis["d_verified"] is True


def test_tool_parameter_analysis() -> None:
    result = RsaHelperTool().run(
        {"mode": "parameters", "n": "3233", "e": "17", "d": "2753", "p": "61", "q": "53"},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["phi"] == 3120
    assert result.data[0]["d_computed"] == 2753
    assert result.data[0]["n_matches_pq"] is True
    assert any(finding.title == "e 与 φ(n) 互质" for finding in result.findings)


def test_n_mismatch_warns() -> None:
    result = RsaHelperTool().run(
        {"mode": "parameters", "n": "9999", "p": "61", "q": "53"},
        _context(),
    )
    assert result.data[0]["n_matches_pq"] is False
    assert any(finding.title == "n 与 p×q 不一致" for finding in result.findings)


def test_invalid_decimal_field_fails() -> None:
    result = RsaHelperTool().run({"mode": "parameters", "p": "abc", "q": "53"}, _context())
    assert result.status is ResultStatus.FAILED
    assert "p 必须是十进制整数" in result.summary


def test_insufficient_parameters_fails() -> None:
    result = RsaHelperTool().run({"mode": "parameters", "e": "17"}, _context())
    assert result.status is ResultStatus.FAILED
    assert "请至少提供 n" in result.summary


def test_pem_public_key_parsing(tmp_path: Path) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem_path = tmp_path / "public.pem"
    pem_path.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    result = RsaHelperTool().run({"mode": "pem", "pem_path": str(pem_path)}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["key_size"] == 2048
    assert result.data[0]["e"] == "65537"
    assert result.data[0]["n"] == str(key.public_key().public_numbers().n)


def test_pem_non_rsa_fails(tmp_path: Path) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    key = ec.generate_private_key(ec.SECP256R1())
    pem_path = tmp_path / "ec.pem"
    pem_path.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    result = RsaHelperTool().run({"mode": "pem", "pem_path": str(pem_path)}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == "公钥不是 RSA 类型。"


def test_pem_invalid_fails(tmp_path: Path) -> None:
    pem_path = tmp_path / "bad.pem"
    pem_path.write_text("not a pem", encoding="utf-8")
    result = RsaHelperTool().run({"mode": "pem", "pem_path": str(pem_path)}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == "无法解析PEM公钥文件。"


def test_pem_missing_file_fails(tmp_path: Path) -> None:
    result = RsaHelperTool().run(
        {"mode": "pem", "pem_path": str(tmp_path / "nope.pem")},
        _context(),
    )
    assert result.status is ResultStatus.FAILED
    assert result.summary == "PEM 文件不存在。"
