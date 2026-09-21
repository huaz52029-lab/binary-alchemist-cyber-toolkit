from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.exceptions import ExportError
from core.exporters import ExportManager
from core.result import ResultStatus, ToolResult


@pytest.fixture
def manager() -> ExportManager:
    return ExportManager.with_defaults()


def test_json_roundtrip(manager: ExportManager, sample_result: ToolResult) -> None:
    payload = json.loads(manager.to_string(sample_result, "json"))
    assert payload["summary"] == "发现 2 条记录"
    assert payload["findings"][0]["severity"] == "MEDIUM"


def test_csv_flattens_data(manager: ExportManager, sample_result: ToolResult) -> None:
    text = manager.to_string(sample_result, "csv")
    assert text.startswith("host,port")
    assert "127.0.0.1,80" in text
    assert "127.0.0.1,443" in text


def test_csv_empty_data_is_empty(manager: ExportManager) -> None:
    result = ToolResult(status=ResultStatus.SUCCESS, summary="no rows")
    assert manager.to_string(result, "csv") == ""


def test_txt_contains_findings(manager: ExportManager, sample_result: ToolResult) -> None:
    text = manager.to_string(sample_result, "txt")
    assert "MEDIUM|HEURISTIC" in text
    assert "示例发现" in text
    assert "证据: evidence: value" in text


def test_export_writes_file(
    manager: ExportManager,
    sample_result: ToolResult,
    tmp_path: Path,
) -> None:
    target = tmp_path / "report.json"
    assert manager.export(sample_result, target) == target
    assert json.loads(target.read_text(encoding="utf-8"))["status"] == "SUCCESS"


def test_export_detects_format_from_suffix(
    manager: ExportManager,
    sample_result: ToolResult,
    tmp_path: Path,
) -> None:
    target = tmp_path / "report.csv"
    manager.export(sample_result, target)
    assert target.read_text(encoding="utf-8-sig").startswith("host,port")


def test_unknown_format_raises(manager: ExportManager, sample_result: ToolResult) -> None:
    with pytest.raises(ExportError):
        manager.to_string(sample_result, "yaml")


def test_missing_suffix_raises(
    manager: ExportManager,
    sample_result: ToolResult,
    tmp_path: Path,
) -> None:
    with pytest.raises(ExportError):
        manager.export(sample_result, tmp_path / "no_suffix")


def test_formats_listing(manager: ExportManager) -> None:
    assert set(manager.formats()) == {"json", "csv", "txt"}
