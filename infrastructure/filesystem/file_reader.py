"""Safe, streaming filesystem read helpers for static analysis."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

from core.exceptions import FileSystemError, TaskCancelledError

DEFAULT_CHUNK_SIZE = 1024 * 1024


def _translate_error(path: Path, exc: OSError) -> FileSystemError:
    if isinstance(exc, FileNotFoundError):
        return FileSystemError(str(exc), user_message="文件不存在。")
    if isinstance(exc, IsADirectoryError):
        return FileSystemError(str(exc), user_message="目标是目录，请选择文件。")
    if isinstance(exc, PermissionError):
        return FileSystemError(
            str(exc),
            user_message="无法读取文件，请检查文件是否存在以及当前用户是否具有读取权限。",
        )
    return FileSystemError(str(exc), user_message="无法读取文件。")


def read_head(path: Path, size: int = 8192) -> bytes:
    """Read up to *size* bytes from the start of a file."""
    try:
        with path.open("rb") as handle:
            return handle.read(size)
    except OSError as exc:
        raise _translate_error(path, exc) from exc


def read_region(path: Path, offset: int, size: int) -> bytes:
    """Read *size* bytes starting at *offset* (bounded by EOF)."""
    try:
        with path.open("rb") as handle:
            handle.seek(offset)
            return handle.read(size)
    except OSError as exc:
        raise _translate_error(path, exc) from exc


def iter_chunks(
    path: Path,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    is_cancelled: Callable[[], bool] | None = None,
) -> Iterator[bytes]:
    """Yield file content chunk by chunk; the whole file is never materialized."""
    try:
        with path.open("rb") as handle:
            while True:
                if is_cancelled is not None and is_cancelled():
                    raise TaskCancelledError()
                chunk = handle.read(chunk_size)
                if not chunk:
                    return
                yield chunk
    except OSError as exc:
        raise _translate_error(path, exc) from exc


def file_snapshot(path: Path) -> tuple[int, int]:
    """Return (size, mtime_ns) used to detect changes during analysis."""
    try:
        stats = path.stat()
    except OSError as exc:
        raise _translate_error(path, exc) from exc
    return stats.st_size, stats.st_mtime_ns


def human_size(size: int) -> str:
    """Human-readable byte size."""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"
