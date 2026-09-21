"""Pure XOR helpers for CTF and learning scenarios."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def hex_to_bytes(value: str) -> bytes:
    compact = "".join(value.split())
    try:
        return bytes.fromhex(compact)
    except ValueError as exc:
        raise ValueError("输入不是有效的Hex数据。") from exc


def xor_single(data: bytes, key: int) -> bytes:
    return bytes(byte ^ key for byte in data)


def xor_repeating(data: bytes, key: bytes) -> bytes:
    if not key:
        raise ValueError("重复密钥XOR需要提供密钥。")
    return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data))


def xor_equal(left: bytes, right: bytes) -> bytes:
    if len(left) != len(right):
        raise ValueError("两个Hex输入长度不同。")
    return bytes(a ^ b for a, b in zip(left, right, strict=True))


def printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    printable = sum(byte in (9, 10, 13) or 32 <= byte <= 126 for byte in data)
    return printable / len(data)


def plaintext_score(data: bytes) -> float:
    """Heuristic: printable ratio plus ASCII letter/space ratio."""
    if not data:
        return 0.0
    printable = sum(byte in (9, 10, 13) or 32 <= byte <= 126 for byte in data)
    letters = sum(byte == 32 or 65 <= byte <= 90 or 97 <= byte <= 122 for byte in data)
    return (printable + letters) / (2 * len(data))


def preview(data: bytes) -> str:
    return "".join(chr(byte) if 32 <= byte <= 126 else "·" for byte in data)


def brute_force_candidates(
    data: bytes,
    *,
    is_cancelled: Callable[[], bool] | None = None,
) -> list[dict[str, Any]]:
    """Score every single-byte key by printable-character ratio."""
    rows: list[dict[str, Any]] = []
    for key in range(256):
        if is_cancelled is not None and is_cancelled():
            from core.exceptions import TaskCancelledError

            raise TaskCancelledError()
        output = xor_single(data, key)
        rows.append(
            {
                "key": key,
                "key_hex": f"0x{key:02x}",
                "score": round(plaintext_score(output) * 100.0, 1),
                "output_hex": output.hex(),
                "preview": preview(output),
            }
        )
    rows.sort(key=lambda row: float(row["score"]), reverse=True)
    return rows
