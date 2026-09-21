"""Shared URL-safe Base64 helpers (used by JWT and auto decode).

JWT segments omit padding; decoding here restores it so no caller re-implements
the same padding logic.
"""

from __future__ import annotations

import base64


def base64url_decode(value: str) -> bytes:
    """Decode an unpadded URL-safe Base64 string (JWT segment)."""
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded)


def base64url_encode(data: bytes) -> str:
    """Encode bytes as unpadded URL-safe Base64."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")
