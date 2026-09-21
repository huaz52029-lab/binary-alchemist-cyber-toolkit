"""Crash report writer: metadata and traceback land in the right file."""

from __future__ import annotations

from pathlib import Path

from core.crash import crash_log_path, write_crash_report


def test_crash_report_contains_metadata_and_traceback(tmp_home: Path) -> None:
    assert crash_log_path() == tmp_home / "logs" / "crash.log"
    path = write_crash_report(ValueError, ValueError("boom"), None)
    content = path.read_text(encoding="utf-8")
    assert "version: 1.0.0" in content
    assert "os: Windows" in content
    assert "boom" in content
