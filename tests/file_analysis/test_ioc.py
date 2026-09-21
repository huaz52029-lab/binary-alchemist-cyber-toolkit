"""Candidate IOC extraction."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.file_analysis.ioc import FileIocTool, extract_iocs


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-fioc",
        tool_id="file_analysis.ioc",
        logger=logging.getLogger("tests.fioc"),
        cancel_event=threading.Event(),
    )


def test_extract_ioc_types() -> None:
    text = (
        "connect to https://example.com/path 192.168.1.1 admin@example.org "
        r"C:\Windows\System32\cmd.exe HKCU\Software\Test 2001:db8::1 "
        "255.255.255.255 0.0.0.0"
    )
    iocs = extract_iocs(text)
    by_type: dict[str, list[str]] = {}
    for ioc in iocs:
        by_type.setdefault(ioc["type"], []).append(ioc["value"])
    assert "https://example.com/path" in by_type["URL"]
    assert "admin@example.org" in by_type["Email"]
    assert "192.168.1.1" in by_type["IPv4"]
    assert "2001:db8::1" in by_type["IPv6"]
    assert r"C:\Windows\System32\cmd.exe" in by_type["WindowsPath"]
    assert "HKCU\\Software\\Test" in by_type["Registry"]
    assert "255.255.255.255" in by_type["IPv4"]
    assert "0.0.0.0" in by_type["IPv4"]
    notes = {ioc["value"]: ioc["note"] for ioc in iocs if ioc["type"] == "IPv4"}
    assert notes["255.255.255.255"] == "受限广播地址"
    assert notes["0.0.0.0"] == "未指定地址"
    assert notes["192.168.1.1"] == "私有地址"


def test_invalid_ip_not_extracted() -> None:
    iocs = extract_iocs("999.999.999.999 123.456.789.0")
    assert all(ioc["type"] != "IPv4" for ioc in iocs)


def test_tool_extracts_from_file(tmp_path: Path) -> None:
    path = tmp_path / "sample.bin"
    path.write_bytes(b"url=https://ctf.example/x ip=10.0.0.1 mail=a@b.com")
    result = FileIocTool().run({"file_path": str(path)}, _context())
    assert result.status is ResultStatus.SUCCESS
    types = {row["type"] for row in result.data}
    assert {"URL", "IPv4", "Email"} <= types
    assert result.findings[0].title == "发现候选 IOC"
    assert "候选" in result.summary
