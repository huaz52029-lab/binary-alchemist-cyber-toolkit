"""Pure codec vectors and error handling for every encoding helper."""

from __future__ import annotations

import pytest

from modules.encoding.codecs import (
    base32_decode,
    base32_encode,
    base58_decode,
    base58_encode,
    base64_decode,
    base64_encode,
    binary_decode,
    binary_encode,
    hex_decode,
    hex_encode,
    html_entity_decode,
    html_entity_encode,
    rot13_transform,
    rot47_transform,
    unicode_escape_decode,
    unicode_escape_encode,
    url_decode,
    url_encode,
)


def test_base64_roundtrip_and_vectors() -> None:
    assert base64_encode("Hello") == "SGVsbG8="
    assert base64_decode("SGVsbG8=") == "Hello"
    assert base64_decode(base64_encode("中文😀")) == "中文😀"


@pytest.mark.parametrize("value", ["!!!!", "SGVsbG8", "A==="])
def test_base64_invalid(value: str) -> None:
    with pytest.raises(ValueError):
        base64_decode(value)


def test_base32_roundtrip_and_case() -> None:
    assert base32_encode("Hello") == "JBSWY3DP"
    assert base32_decode("jbsWy3dp") == "Hello"
    assert base32_decode(base32_encode("你好")) == "你好"


def test_base32_invalid() -> None:
    with pytest.raises(ValueError):
        base32_decode("!!!!")


def test_base58_roundtrip_and_vector() -> None:
    assert base58_encode("Hello World!") == "2NEpo7TZRRrLZSi2U"
    assert base58_decode("2NEpo7TZRRrLZSi2U") == "Hello World!"
    assert base58_decode(base58_encode("中文测试")) == "中文测试"


def test_base58_invalid() -> None:
    with pytest.raises(ValueError):
        base58_decode("0OIl")


def test_hex_roundtrip_and_variants() -> None:
    assert hex_encode("Hello") == "48656c6c6f"
    assert hex_decode("48 65 6c 6c 6f") == "Hello"
    assert hex_decode("48656C6C6F") == "Hello"


@pytest.mark.parametrize("value", ["abc", "486", "zz"])
def test_hex_invalid(value: str) -> None:
    with pytest.raises(ValueError):
        hex_decode(value)


def test_binary_roundtrip() -> None:
    assert binary_encode("A") == "01000001"
    assert binary_decode("01001000 01100101") == "He"


def test_binary_invalid() -> None:
    with pytest.raises(ValueError):
        binary_decode("01001000 012")
    with pytest.raises(ValueError):
        binary_decode("0100")


def test_url_roundtrip() -> None:
    assert url_encode("hello world") == "hello%20world"
    assert url_decode("hello%20world") == "hello world"
    assert url_decode(url_encode("https://example.com/a b?id=hello world")) == (
        "https://example.com/a b?id=hello world"
    )


def test_url_invalid_utf8() -> None:
    with pytest.raises(ValueError):
        url_decode("%ff%fe")


def test_unicode_roundtrip() -> None:
    assert unicode_escape_encode("你好") == "\\u4f60\\u597d"
    assert unicode_escape_decode("\\u4f60\\u597d") == "你好"
    assert unicode_escape_decode(unicode_escape_encode("abc😀")) == "abc😀"


def test_unicode_invalid() -> None:
    with pytest.raises(ValueError):
        unicode_escape_decode("\\uZZZZ")


def test_rot13() -> None:
    assert rot13_transform("hello") == "uryyb"
    assert rot13_transform(rot13_transform("Hello World")) == "Hello World"


def test_rot47() -> None:
    assert rot47_transform("!") == "P"
    assert rot47_transform("~") == "O"
    assert rot47_transform(rot47_transform("The Quick Brown Fox")) == "The Quick Brown Fox"
    assert rot47_transform("你好 ") == "你好 "


def test_html_entity_roundtrip() -> None:
    assert html_entity_encode("<") == "&lt;"
    assert html_entity_encode('a<b&"c') == "a&lt;b&amp;&quot;c"
    assert html_entity_decode("&lt;div&gt;") == "<div>"
    assert html_entity_decode(html_entity_encode("<script>")) == "<script>"
