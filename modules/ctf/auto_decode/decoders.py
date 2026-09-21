"""Heuristic multi-encoding candidates with bounded multi-layer search."""

from __future__ import annotations

import base64
import gzip
import json
import re
import unicodedata
import zlib
from dataclasses import dataclass, field

from infrastructure.crypto.base64url import base64url_decode
from modules.encoding.codecs import (
    base32_decode,
    base58_decode,
    base64_decode,
    binary_decode,
    hex_decode,
    html_entity_decode,
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
    chain: tuple[str, ...] = field(default_factory=tuple)
    depth: int = 1


MAX_DECODED_LENGTH = 100_000
MAX_CANDIDATES = 200


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


def _attempt_base64url(text: str) -> str:
    value = text.strip()
    if "-" not in value and "_" not in value:
        raise ValueError("not base64url-shaped")
    if len(value) % 4 == 1:
        raise ValueError("not base64url-shaped")
    try:
        return base64url_decode(value).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("invalid base64url") from exc


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


def _attempt_html_entity(text: str) -> str:
    if "&" not in text or not re.search(r"&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);", text):
        raise ValueError("no html entities")
    decoded = html_entity_decode(text)
    if decoded == text:
        raise ValueError("no change")
    return decoded


def _attempt_json(text: str) -> str:
    value = text.strip()
    if not value.startswith(("{", "[")):
        raise ValueError("not json-shaped")
    parsed = json.loads(value)
    return json.dumps(parsed, ensure_ascii=False, indent=2)


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


def _binary_payload(text: str) -> bytes:
    value = text.strip()
    try:
        return base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise ValueError("not base64") from exc


def _attempt_gzip(text: str) -> str:
    try:
        return gzip.decompress(_binary_payload(text)).decode("utf-8")
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("not base64+gzip") from exc


def _attempt_deflate(text: str) -> str:
    data = _binary_payload(text)
    for wbits in (-15, 15):
        try:
            return zlib.decompress(data, wbits).decode("utf-8")
        except (zlib.error, UnicodeDecodeError):
            continue
    raise ValueError("not base64+deflate")


_DECODERS = (
    ("Base64", _attempt_base64, 0.95, "标准 Base64（可含 = 填充）"),
    ("Base64URL", _attempt_base64url, 0.93, "URL-safe Base64（无填充）"),
    ("Base32", _attempt_base32, 0.9, "Base32（大小写不敏感）"),
    ("Base58", _attempt_base58, 0.85, "Base58（Bitcoin 字母表）"),
    ("Hex", _attempt_hex, 0.9, "十六进制字节串"),
    ("Binary", _attempt_binary, 0.9, "8 位二进制（空格分隔）"),
    ("URL", _attempt_url, 0.7, "URL 百分号解码"),
    ("Unicode", _attempt_unicode, 0.8, "Unicode \\uXXXX 转义"),
    ("HTML Entity", _attempt_html_entity, 0.75, "HTML 实体解码"),
    ("JSON", _attempt_json, 0.8, "格式化 JSON"),
    ("ROT13", _attempt_rot13, 0.5, "ROT13 字母旋转"),
    ("ROT47", _attempt_rot47, 0.5, "ROT47 ASCII 旋转"),
    ("Base64→Gzip", _attempt_gzip, 0.95, "Base64 后接 Gzip 压缩"),
    ("Base64→Deflate", _attempt_deflate, 0.9, "Base64 后接 Deflate 压缩"),
    ("JWT", _attempt_jwt, 0.98, "JWT（header.payload.signature）"),
)


def decode_candidates(
    text: str,
    *,
    max_depth: int = 5,
    max_candidates: int = MAX_CANDIDATES,
) -> list[DecoderCandidate]:
    """Breadth-first multi-layer decoding with cycle and depth limits."""
    queue: list[tuple[str, tuple[str, ...], int, float]] = [(text, (), 0, 1.0)]
    seen = {text}
    candidates: list[DecoderCandidate] = []
    while queue and len(candidates) < max_candidates:
        value, chain, depth, cumulative = queue.pop(0)
        if depth >= max_depth:
            continue
        for name, attempt, base_score, description in _DECODERS:
            try:
                decoded = attempt(value)
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if decoded == value or decoded in seen or len(decoded) > MAX_DECODED_LENGTH:
                continue
            ratio = _printable_ratio(decoded)
            if ratio < 0.7:
                continue
            score = cumulative * base_score * ratio
            candidates.append(
                DecoderCandidate(
                    name=name,
                    level=_confidence_level(score),
                    score=round(score, 3),
                    decoded=decoded,
                    description=description,
                    chain=(*chain, name),
                    depth=depth + 1,
                )
            )
            if depth + 1 < max_depth and len(candidates) < max_candidates:
                seen.add(decoded)
                queue.append((decoded, (*chain, name), depth + 1, cumulative * base_score))
    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    return candidates[:max_candidates]
