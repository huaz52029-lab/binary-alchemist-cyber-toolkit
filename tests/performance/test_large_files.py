"""100MB file stability: streaming hash/strings/entropy and paged hex view."""

from __future__ import annotations

import hashlib
import logging
import threading
import tracemalloc
from pathlib import Path

import pytest

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.file_analysis.entropy import FileEntropyTool
from modules.file_analysis.hashes import FileHashesTool
from modules.file_analysis.hex_viewer import FileHexViewerTool
from modules.file_analysis.strings import FileStringsTool

MEGABYTE = 1024 * 1024


def _context(tool_id: str) -> ExecutionContext:
    return ExecutionContext(
        task_id="t-large",
        tool_id=tool_id,
        logger=logging.getLogger("tests.large"),
        cancel_event=threading.Event(),
    )


@pytest.fixture
def large_file(tmp_path: Path) -> Path:
    """A 100MB file with readable runs and random padding, written in chunks."""
    path = tmp_path / "large.bin"
    block = "hello 网安 test string ABCDEFGH ".encode() * 8192 + bytes(range(256)) * 32
    block = block * ((MEGABYTE // len(block)) + 1)
    block = block[:MEGABYTE]
    with path.open("wb") as handle:
        for _ in range(100):
            handle.write(block)
    return path


def _expected_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(MEGABYTE):
            digest.update(chunk)
    return digest.hexdigest()


def test_hash_streams_without_loading_file(large_file: Path) -> None:
    tracemalloc.start()
    try:
        result = FileHashesTool().run({"file_path": str(large_file)}, _context("file.hashes"))
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["sha256"] == _expected_sha256(large_file)
    assert peak < 64 * MEGABYTE, "100MB file must not be materialized in memory"


def test_strings_scans_large_file(large_file: Path) -> None:
    result = FileStringsTool().run(
        {"file_path": str(large_file), "min_length": 4},
        _context("file.strings"),
    )
    assert result.status is ResultStatus.SUCCESS
    texts = " ".join(row.get("text", "") for row in result.data)
    assert "hello" in texts


def test_entropy_handles_large_file(large_file: Path) -> None:
    result = FileEntropyTool().run({"file_path": str(large_file)}, _context("file.entropy"))
    assert result.status is ResultStatus.SUCCESS
    entropy = result.data[0].get("entropy")
    assert isinstance(entropy, float)
    assert 0.0 <= entropy <= 8.0


def test_hex_viewer_reads_one_page_only(large_file: Path) -> None:
    result = FileHexViewerTool().run(
        {"file_path": str(large_file), "offset": "0x100000", "length": 256},
        _context("file.hex_viewer"),
    )
    assert result.status is ResultStatus.SUCCESS
    assert result.data
