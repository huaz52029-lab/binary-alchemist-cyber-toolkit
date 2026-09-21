"""MD5 reverse: validation, hashing vectors and candidate generators."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.exceptions import ToolInputError
from infrastructure.crypto import md5_hexdigest
from modules.crypto.md5_reverse import (
    iter_bruteforce_candidates,
    iter_dictionary_candidates,
    normalize_charset,
    parse_target_hashes,
    search_space,
)
from modules.crypto.md5_reverse.validators import (
    INVALID_HASH_MESSAGE,
    MAX_BRUTE_LENGTH,
    MAX_CHARSET_LENGTH,
    validate_brute_lengths,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", "d41d8cd98f00b204e9800998ecf8427e"),
        ("hello", "5d41402abc4b2a76b9719d911017c592"),
        ("world", "7d793037a0760186574b0282f2f435e7"),
        ("abc", "900150983cd24fb0d6963f7d28e17f72"),
    ],
)
def test_known_md5_vectors(text: str, expected: str) -> None:
    assert md5_hexdigest(text) == expected


def test_parse_target_hashes_normalizes_and_splits() -> None:
    hashes = parse_target_hashes(
        " 5D41402ABC4B2A76B9719D911017C592\n7d793037a0760186574b0282f2f435e7, "
        "900150983cd24fb0d6963f7d28e17f72"
    )
    assert hashes == [
        "5d41402abc4b2a76b9719d911017c592",
        "7d793037a0760186574b0282f2f435e7",
        "900150983cd24fb0d6963f7d28e17f72",
    ]


@pytest.mark.parametrize("raw", ["12345", "z" * 32, "g" + "0" * 31])
def test_parse_target_hashes_invalid(raw: str) -> None:
    with pytest.raises(ToolInputError) as exc_info:
        parse_target_hashes(raw)
    assert exc_info.value.user_message == INVALID_HASH_MESSAGE


@pytest.mark.parametrize("raw", ["", "   "])
def test_parse_target_hashes_empty(raw: str) -> None:
    with pytest.raises(ToolInputError) as exc_info:
        parse_target_hashes(raw)
    assert exc_info.value.user_message == "请输入目标MD5 Hash。"


def test_normalize_charset_dedupes() -> None:
    assert normalize_charset("aabbcc") == "abc"
    assert normalize_charset("zyxzyx") == "zyx"


def test_normalize_charset_errors() -> None:
    with pytest.raises(ToolInputError):
        normalize_charset("")
    too_large = "".join(chr(33 + index) for index in range(MAX_CHARSET_LENGTH + 1))
    with pytest.raises(ToolInputError):
        normalize_charset(too_large)


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [(0, 5), (2, 1), (1, MAX_BRUTE_LENGTH + 1), (-1, 3)],
)
def test_validate_brute_lengths_errors(minimum: int, maximum: int) -> None:
    with pytest.raises(ToolInputError):
        validate_brute_lengths(minimum, maximum)


def test_validate_brute_lengths_ok() -> None:
    assert validate_brute_lengths(1, 5) == (1, 5)


def test_search_space() -> None:
    assert search_space("ab", 1, 2) == 6  # 2 + 4
    assert search_space("abc", 3, 3) == 27


def test_dictionary_generator(tmp_path: Path) -> None:
    path = tmp_path / "dict.txt"
    path.write_text("hello\n world \n\nlast\n", encoding="utf-8")
    candidates = list(iter_dictionary_candidates(path))
    assert candidates == ["hello", " world ", "", "last"]


def test_bruteforce_generator_order() -> None:
    candidates = list(iter_bruteforce_candidates("ab", 1, 2))
    assert candidates == ["a", "b", "aa", "ab", "ba", "bb"]
