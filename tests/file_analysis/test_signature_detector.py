"""Magic-byte type detection."""

from __future__ import annotations

import pytest

from infrastructure.filesystem import FileTypeDetector


@pytest.mark.parametrize(
    ("head", "expected"),
    [
        (b"MZ\x90\x00", "PE"),
        (b"%PDF-1.7", "PDF"),
        (b"\x89PNG\r\n\x1a\n", "PNG"),
        (b"\xff\xd8\xff\xe0", "JPEG"),
        (b"GIF89a", "GIF"),
        (b"PK\x03\x04", "ZIP"),
        (b"Rar!\x1a\x07", "RAR"),
        (b"\x1f\x8b\x08", "GZIP"),
        (b"\x7fELF", "ELF"),
        (b"SQLite format 3\x00", "SQLite"),
        (b"hello world, plain text", "Text"),
        (b"\x00\x01\x02\x03\xff\xfe\xfd", "Unknown"),
    ],
)
def test_detect_bytes(head: bytes, expected: str) -> None:
    assert FileTypeDetector.detect_bytes(head).detected_type == expected


def test_extension_mapping() -> None:
    assert FileTypeDetector.expected_from_extension("a.exe") == "PE"
    assert FileTypeDetector.expected_from_extension("a.pdf") == "PDF"
    assert FileTypeDetector.expected_from_extension("noext") is None
