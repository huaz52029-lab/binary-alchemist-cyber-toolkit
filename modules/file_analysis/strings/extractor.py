"""Streaming printable-string extraction for ASCII / UTF-8 / UTF-16LE."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from infrastructure.filesystem import iter_chunks

KEYWORDS = (
    "http",
    "https",
    "powershell",
    "cmd.exe",
    "reg.exe",
    "CreateProcess",
    "VirtualAlloc",
    "WinExec",
    "LoadLibrary",
    "GetProcAddress",
)

_ASCII_PATTERN = re.compile(rb"[\x20-\x7e]{4,}")
_UTF8_RUN = re.compile(rb"(?:[\x20-\x7e]|[\x80-\xff]){4,}")
_UTF16_PATTERN = re.compile(r"[^\x00-\x1f\x7f-\x9f\ufffd]{4,}")


@dataclass(frozen=True, slots=True)
class StringRecord:
    offset: int
    encoding: str
    length: int
    text: str


def keyword_hints(text: str) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in KEYWORDS if keyword.lower() in lowered]


def _scan_ascii(data: bytes, base: int, min_length: int) -> Iterator[StringRecord]:
    for match in _ASCII_PATTERN.finditer(data):
        if len(match.group()) >= min_length:
            yield StringRecord(
                offset=base + match.start(),
                encoding="ASCII",
                length=len(match.group()),
                text=match.group().decode("ascii"),
            )


def _scan_utf8(data: bytes, base: int, min_length: int) -> Iterator[StringRecord]:
    for match in _UTF8_RUN.finditer(data):
        run = match.group()
        if len(run) < min_length:
            continue
        try:
            text = run.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if len(text) >= min_length:
            yield StringRecord(
                offset=base + match.start(),
                encoding="UTF-8",
                length=len(run),
                text=text,
            )


def _scan_utf16le(data: bytes, base: int, min_length: int) -> Iterator[StringRecord]:
    even = data[: len(data) - len(data) % 2]
    text = even.decode("utf-16-le", errors="replace")
    for match in _UTF16_PATTERN.finditer(text):
        if len(match.group()) >= min_length:
            yield StringRecord(
                offset=base + match.start() * 2,
                encoding="UTF-16LE",
                length=len(match.group()),
                text=match.group(),
            )


def extract_strings(
    path: Path,
    *,
    encoding: str = "ascii",
    min_length: int = 4,
    chunk_size: int = 1024 * 1024,
    max_results: int = 20_000,
    is_cancelled: Callable[[], bool] | None = None,
    on_progress: Callable[[int], None] | None = None,
) -> list[StringRecord]:
    """Stream the file and collect printable strings up to *max_results*."""
    scanner = {"ascii": _scan_ascii, "utf8": _scan_utf8, "utf16le": _scan_utf16le}[encoding]
    records: list[StringRecord] = []
    carry = b""
    base = 0
    for chunk in iter_chunks(path, chunk_size=chunk_size, is_cancelled=is_cancelled):
        data = carry + chunk
        for record in scanner(data, base - len(carry), min_length):
            records.append(record)
            if len(records) >= max_results:
                return records
        carry = data[-max(0, min_length - 1) :]
        base += len(chunk)
        if on_progress is not None:
            on_progress(base)
    return records
