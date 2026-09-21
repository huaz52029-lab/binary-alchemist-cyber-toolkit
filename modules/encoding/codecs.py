"""Pure text encoding/decoding helpers shared by tools and auto decode.

Every function raises ``ValueError`` with a human-readable message on invalid
input; tools translate that into a failed ToolResult, never a raw traceback.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import html
import re
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass


def _decode_utf8(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label}解码结果不是有效的UTF-8文本。") from exc


# ---------------------------------------------------------------- Base64


def base64_encode(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def base64_decode(text: str) -> str:
    try:
        data = base64.b64decode(text.strip(), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("输入不是有效的Base64数据。") from exc
    return _decode_utf8(data, "Base64")


# ---------------------------------------------------------------- Base32


def base32_encode(text: str) -> str:
    return base64.b32encode(text.encode("utf-8")).decode("ascii")


def base32_decode(text: str) -> str:
    try:
        data = base64.b32decode(text.strip().upper(), casefold=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("输入不是有效的Base32数据。") from exc
    return _decode_utf8(data, "Base32")


# ---------------------------------------------------------------- Base58

_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_BASE58_INDEX = {char: index for index, char in enumerate(_BASE58_ALPHABET)}


def base58_encode(text: str) -> str:
    data = text.encode("utf-8")
    value = int.from_bytes(data, "big")
    output: list[str] = []
    while value > 0:
        value, remainder = divmod(value, 58)
        output.append(_BASE58_ALPHABET[remainder])
    for byte in data:
        if byte == 0:
            output.append("1")
        else:
            break
    return "".join(reversed(output)) or "1"


def base58_decode(text: str) -> str:
    value = text.strip()
    if not value:
        raise ValueError("输入不是有效的Base58数据。")
    number = 0
    for char in value:
        if char not in _BASE58_INDEX:
            raise ValueError("输入不是有效的Base58数据。")
        number = number * 58 + _BASE58_INDEX[char]
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    padding = len(value) - len(value.lstrip("1"))
    data = b"\x00" * padding + raw
    return _decode_utf8(data, "Base58")


# ---------------------------------------------------------------- Hex


def hex_encode(text: str) -> str:
    return text.encode("utf-8").hex()


def hex_decode(text: str) -> str:
    compact = "".join(text.split())
    try:
        data = bytes.fromhex(compact)
    except ValueError as exc:
        raise ValueError("输入不是有效的Hex数据（需为偶数个十六进制字符）。") from exc
    return _decode_utf8(data, "Hex")


# ---------------------------------------------------------------- Binary


def binary_encode(text: str) -> str:
    return " ".join(f"{byte:08b}" for byte in text.encode("utf-8"))


def binary_decode(text: str) -> str:
    tokens = text.split()
    if not tokens or any(len(token) != 8 or set(token) - {"0", "1"} for token in tokens):
        raise ValueError("二进制输入只能包含由空格分隔的8位0/1。")
    data = bytes(int(token, 2) for token in tokens)
    return _decode_utf8(data, "二进制")


# ---------------------------------------------------------------- URL


def url_encode(text: str) -> str:
    return urllib.parse.quote(text, safe="")


def url_decode(text: str) -> str:
    try:
        return urllib.parse.unquote(text, encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("URL解码结果不是有效的UTF-8文本。") from exc


# ---------------------------------------------------------------- Unicode escape


def unicode_escape_encode(text: str) -> str:
    return text.encode("unicode_escape").decode("ascii")


def unicode_escape_decode(text: str) -> str:
    if re.search(r"\\u(?![\da-fA-F]{4})|\\U(?![\da-fA-F]{8})", text):
        raise ValueError("输入包含无效的Unicode转义序列。")
    try:
        return codecs.decode(text, "unicode_escape")
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("输入包含无效的Unicode转义序列。") from exc


# ---------------------------------------------------------------- ROT13 / ROT47


def rot13_transform(text: str) -> str:
    return codecs.encode(text, "rot_13")


def rot47_transform(text: str) -> str:
    output: list[str] = []
    for char in text:
        code = ord(char)
        if 33 <= code <= 126:
            output.append(chr(33 + (code - 33 + 47) % 94))
        else:
            output.append(char)
    return "".join(output)


# ---------------------------------------------------------------- HTML entities


def html_entity_encode(text: str) -> str:
    return html.escape(text, quote=True)


def html_entity_decode(text: str) -> str:
    return html.unescape(text)


@dataclass(frozen=True, slots=True)
class Codec:
    """A named, reversible text transform."""

    name: str
    encode: Callable[[str], str]
    decode: Callable[[str], str]


CODECS: dict[str, Codec] = {
    "base64": Codec("Base64", base64_encode, base64_decode),
    "base32": Codec("Base32", base32_encode, base32_decode),
    "base58": Codec("Base58", base58_encode, base58_decode),
    "hex": Codec("Hex", hex_encode, hex_decode),
    "binary": Codec("Binary", binary_encode, binary_decode),
    "url": Codec("URL", url_encode, url_decode),
    "unicode": Codec("Unicode", unicode_escape_encode, unicode_escape_decode),
    "rot13": Codec("ROT13", rot13_transform, rot13_transform),
    "rot47": Codec("ROT47", rot47_transform, rot47_transform),
    "html_entity": Codec("HTML Entity", html_entity_encode, html_entity_decode),
}
