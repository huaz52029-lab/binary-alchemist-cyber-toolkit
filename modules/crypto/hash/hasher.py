"""Chunked hashing helpers (never loads a whole file into memory)."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

from core.exceptions import TaskCancelledError

ALGORITHMS = ("MD5", "SHA1", "SHA224", "SHA256", "SHA384", "SHA512")
CHUNK_SIZE = 1024 * 1024


def hash_text(text: str, algorithm: str) -> str:
    return hashlib.new(algorithm.lower(), text.encode("utf-8")).hexdigest()


def hash_file(
    path: Path,
    algorithm: str,
    *,
    is_cancelled: Callable[[], bool] | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> str:
    """Hash a file in chunks with optional cancellation and progress."""
    digest = hashlib.new(algorithm.lower())
    size = path.stat().st_size
    with path.open("rb") as handle:
        while True:
            if is_cancelled is not None and is_cancelled():
                raise TaskCancelledError()
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
            if on_progress is not None and size > 0:
                on_progress(min(100.0, handle.tell() / size * 100.0))
    return digest.hexdigest()
