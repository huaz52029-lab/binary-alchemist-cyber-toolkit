"""Heuristic multi-encoding candidate detection for Auto Decode."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass

from infrastructure.crypto.base64url import base64url_decode
from modules.encoding.codecs import (
    base32_decode,
    base58_decode,
    base64_decode,
    binary_decode,
    hex_decode,
    rot13_transform,
    rot47_transform,
    unicode_escape_decode,
    url_decode,
)


@dataclass(frozen=True, slots=True)
class DecoderCandidate:
    """One heuristic decoding candidate; never a certainty."""

    name: str
    level: str
    score: float
    decoded: str
    description: str


def _printable_ratio(text: str) -> float:
    if not text:
        return 0.0
    printable = sum(
        char in "\t\n\r" or not unicodedata.category(char).startswith("C") for char in text
    )
    return printable / len(text)


def _confidence_level(score: float) -> str:
    if score >= 0.85:
        return "High"
    if score >= 0.55:
        return "Medium"
    return "Low"


def _attempt_base64(text: str) -> str:
    value = text.strip()
    if "=" in value or len(value) % 4 == 0:
        return base64_decode(text)
    raise ValueError("not base64-shaped")


def _attempt_base32(text: str) -> str:
    value = text.strip()
    if len(value) % 8 == 0:
        return base32_decode(text)
    raise ValueError("not base32-shaped")


def _attempt_base58(text: str) -> str:
    value = text.strip()
    if not value or set(value) - set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"):
        raise ValueError("not base58-shaped")
    return base58_decode(text)


def _attempt_hex(text: str) -> str:
    value = "".join(text.split())
    if len(value) >= 2 and len(value) % 2 == 0 and re.fullmatch(r"[0-9a-fA-F]+", value):
        return hex_decode(text)
    raise ValueError("not hex-shaped")


def _attempt_binary(text: str) -> str:
    tokens = text.split()
    if tokens and all(len(token) == 8 and set(token) <= {"0", "1"} for token in tokens):
        return binary_decode(text)
    raise ValueError("not binary-shaped")


def _attempt_url(text: str) -> str:
    if "%" not in text:
        raise ValueError("no percent sequences")
    decoded = url_decode(text)
    if decoded == text:
        raise ValueError("no change")
    return decoded


def _attempt_unicode(text: str) -> str:
    if "\\u" not in text and "\\U" not in text:
        raise ValueError("no unicode escapes")
    return unicode_escape_decode(text)


def _attempt_rot13(text: str) -> str:
    if not re.search(r"[a-zA-Z]", text):
        raise ValueError("no letters")
    decoded = rot13_transform(text)
    if decoded == text:
        raise ValueError("no change")
    return decoded


def _attempt_rot47(text: str) -> str:
    decoded = rot47_transform(text)
    if decoded == text:
        raise ValueError("no change")
    return decoded


def _attempt_jwt(text: str) -> str:
    parts = text.strip().split(".")
    if len(parts) != 3:
        raise ValueError("not a 3-part JWT")
    header = json.loads(base64url_decode(parts[0]).decode("utf-8"))
    payload = json.loads(base64url_decode(parts[1]).decode("utf-8"))
    return (
        "Header:\n"
        + json.dumps(header, ensure_ascii=False, indent=2)
        + "\n\nPayload:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


_DECODERS = [
    ("Base64", _attempt_base64, 0.95, "标准 Base64（可含 = 填充）"),
    ("Base32", _attempt_base32, 0.9, "Base32（大小写不敏感）"),
    ("Base58", _attempt_base58, 0.85, "Base58（Bitcoin 字母表）"),
    ("Hex", _attempt_hex, 0.9, "十六进制字节串"),
    ("Binary", _attempt_binary, 0.9, "8 位二进制（空格分隔）"),
    ("URL", _attempt_url, 0.7, "URL 百分号解码"),
    ("Unicode", _attempt_unicode, 0.8, "Unicode \\uXXXX 转义"),
    ("ROT13", _attempt_rot13, 0.5, "ROT13 字母旋转"),
    ("ROT47", _attempt_rot47, 0.5, "ROT47 ASCII 旋转"),
    ("JWT", _attempt_jwt, 0.98, "JWT（header.payload.signature）"),
]


def decode_candidates(text: str) -> list[DecoderCandidate]:
    """Try every registered decoder and return scored candidates."""
    candidates: list[DecoderCandidate] = []
    for name, attempt, base_score, description in _DECODERS:
        try:
            decoded = attempt(text)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        ratio = _printable_ratio(decoded)
        if ratio < 0.7:
            continue
        score = base_score * ratio
        candidates.append(
            DecoderCandidate(
                name=name,
                level=_confidence_level(score),
                score=round(score, 3),
                decoded=decoded,
                description=description,
            )
        )
    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    return candidates
