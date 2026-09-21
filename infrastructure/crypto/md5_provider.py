"""Thin, shared MD5 digest helper.

Candidates are always encoded as UTF-8 before hashing, which the UI states
explicitly so identical text never produces different results across tools.
"""

from __future__ import annotations

import hashlib


def md5_hexdigest(text: str) -> str:
    """Return the lowercase MD5 hex digest of *text* (UTF-8)."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()
