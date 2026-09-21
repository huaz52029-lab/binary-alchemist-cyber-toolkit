"""Validation and normalization helpers for the MD5 reverse tool."""

from __future__ import annotations

import re

from core.exceptions import ToolInputError

HASH_PATTERN = re.compile(r"^[0-9a-f]{32}$")
INVALID_HASH_MESSAGE = "无效的MD5 Hash，应为32位十六进制字符。"
MAX_BRUTE_LENGTH = 8
MAX_CHARSET_LENGTH = 94
LARGE_SPACE_THRESHOLD = 1_000_000


def normalize_hash(value: str) -> str:
    """Strip surrounding whitespace and lowercase a hash."""
    return value.strip().lower()


def parse_target_hashes(raw: str) -> list[str]:
    """Parse one or more MD5 hashes separated by whitespace, commas or semicolons."""
    tokens = re.split(r"[\s,;]+", raw.strip())
    hashes = [normalize_hash(token) for token in tokens if token]
    if not hashes:
        raise ToolInputError("empty hash input", user_message="请输入目标MD5 Hash。")
    for value in hashes:
        if not HASH_PATTERN.match(value):
            raise ToolInputError(
                f"invalid md5 hash (length={len(value)})",
                user_message=INVALID_HASH_MESSAGE,
            )
    return hashes


def normalize_charset(charset: str) -> str:
    """Deduplicate the charset while preserving order and validate its size."""
    if not charset:
        raise ToolInputError("empty charset", user_message="字符集不能为空。")
    deduped = "".join(dict.fromkeys(charset))
    if len(deduped) > MAX_CHARSET_LENGTH:
        raise ToolInputError(
            f"charset too large: {len(deduped)}",
            user_message=f"字符集最多允许 {MAX_CHARSET_LENGTH} 个不同字符。",
        )
    return deduped


def validate_brute_lengths(min_length: int, max_length: int) -> tuple[int, int]:
    """Validate brute-force length bounds and return them normalized."""
    if min_length < 1 or max_length > MAX_BRUTE_LENGTH or min_length > max_length:
        raise ToolInputError(
            f"invalid lengths: {min_length}-{max_length}",
            user_message=(f"暴力长度需满足 1 ≤ 最小长度 ≤ 最大长度 ≤ {MAX_BRUTE_LENGTH}。"),
        )
    return min_length, max_length


def search_space(charset: str, min_length: int, max_length: int) -> int:
    """Total candidate count: sum(len(charset)**L for L in min..max)."""
    base = len(charset)
    return sum(base**length for length in range(min_length, max_length + 1))
