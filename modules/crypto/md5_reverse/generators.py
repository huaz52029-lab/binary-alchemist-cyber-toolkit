"""Streaming candidate generators; the full space is never materialized."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from itertools import product
from pathlib import Path


def iter_dictionary_candidates(
    path: Path,
    *,
    on_read: Callable[[int], None] | None = None,
) -> Iterator[str]:
    """Yield dictionary lines one at a time.

    Only CR/LF line endings are stripped (``rstrip("\\r\\n")``); leading and
    trailing spaces of the candidate itself are preserved, so ``" hello "`` and
    ``"hello"`` stay distinct candidates. The file is read in binary mode and
    decoded per line with strict UTF-8 so read offsets stay reliable.
    """
    with path.open("rb") as handle:
        for raw_line in handle:
            yield raw_line.decode("utf-8", errors="strict").rstrip("\r\n")
            if on_read is not None:
                on_read(handle.tell())


def iter_bruteforce_candidates(
    charset: str,
    min_length: int,
    max_length: int,
) -> Iterator[str]:
    """Yield every combination of *charset* from min to max length."""
    for length in range(min_length, max_length + 1):
        for combo in product(charset, repeat=length):
            yield "".join(combo)
