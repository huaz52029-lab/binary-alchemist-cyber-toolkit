"""Magic-bytes based file type detection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from infrastructure.filesystem.file_reader import read_head


@dataclass(frozen=True, slots=True)
class FileTypeResult:
    detected_type: str
    magic_hex: str
    description: str


SIGNATURES: tuple[tuple[str, bytes, str], ...] = (
    ("PE", b"MZ", "PE 可执行文件（DOS MZ 头）"),
    ("PDF", b"%PDF", "PDF 文档"),
    ("PNG", b"\x89PNG\r\n\x1a\n", "PNG 图像"),
    ("JPEG", b"\xff\xd8\xff", "JPEG 图像"),
    ("GIF", b"GIF8", "GIF 图像"),
    ("ZIP", b"PK\x03\x04", "ZIP 压缩包"),
    ("ZIP", b"PK\x05\x06", "ZIP 压缩包（空）"),
    ("RAR", b"Rar!\x1a\x07", "RAR 压缩包"),
    ("GZIP", b"\x1f\x8b", "GZIP 压缩数据"),
    ("ELF", b"\x7fELF", "ELF 可执行文件"),
    ("SQLite", b"SQLite format 3\x00", "SQLite 数据库"),
)

EXTENSION_TYPES: dict[str, str] = {
    ".exe": "PE",
    ".dll": "PE",
    ".sys": "PE",
    ".pdf": "PDF",
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".gif": "GIF",
    ".zip": "ZIP",
    ".rar": "RAR",
    ".gz": "GZIP",
    ".elf": "ELF",
    ".sqlite": "SQLite",
    ".db": "SQLite",
    ".txt": "Text",
}


def _looks_like_text(head: bytes) -> bool:
    if not head:
        return False
    nulls = head.count(b"\x00")
    if nulls > len(head) * 0.01:
        return False
    printable = sum(byte in (9, 10, 13) or 32 <= byte <= 126 for byte in head)
    return printable / len(head) >= 0.9


class FileTypeDetector:
    """Detects file type from magic bytes, falling back to text heuristics."""

    def __init__(self, head_size: int = 8192) -> None:
        self._head_size = head_size

    def detect(self, path: Path) -> FileTypeResult:
        return self.detect_bytes(read_head(path, self._head_size))

    @staticmethod
    def detect_bytes(head: bytes) -> FileTypeResult:
        for name, signature, description in SIGNATURES:
            if head.startswith(signature):
                return FileTypeResult(
                    detected_type=name,
                    magic_hex=signature.hex(" ").upper(),
                    description=description,
                )
        if _looks_like_text(head):
            return FileTypeResult(
                detected_type="Text",
                magic_hex="",
                description="可打印文本",
            )
        return FileTypeResult(
            detected_type="Unknown",
            magic_hex=head[:16].hex(" ").upper(),
            description="未识别的二进制数据",
        )

    @staticmethod
    def expected_from_extension(name: str) -> str | None:
        return EXTENSION_TYPES.get(Path(name).suffix.lower())
