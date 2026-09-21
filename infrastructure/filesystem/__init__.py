"""Filesystem adapters: streaming file reader and magic-byte signature detection."""

from infrastructure.filesystem.file_reader import (
    file_snapshot,
    human_size,
    iter_chunks,
    read_head,
    read_region,
)
from infrastructure.filesystem.signature_detector import (
    EXTENSION_TYPES,
    FileTypeDetector,
    FileTypeResult,
)

__all__ = [
    "EXTENSION_TYPES",
    "FileTypeDetector",
    "FileTypeResult",
    "file_snapshot",
    "human_size",
    "iter_chunks",
    "read_head",
    "read_region",
]
