"""Multi-layer auto decode: chains, depth limits and cycle detection."""

from __future__ import annotations

import base64

from modules.ctf.auto_decode.decoders import decode_candidates


def test_double_base64() -> None:
    encoded = base64.b64encode(base64.b64encode(b"hello")).decode()
    candidates = decode_candidates(encoded, max_depth=3)
    chained = next(candidate for candidate in candidates if candidate.chain == ("Base64", "Base64"))
    assert chained.depth == 2
    assert chained.decoded == "hello"


def test_base64_then_hex() -> None:
    inner = b"hello".hex()
    encoded = base64.b64encode(inner.encode()).decode()
    candidates = decode_candidates(encoded, max_depth=3)
    chain_candidate = next(
        candidate for candidate in candidates if candidate.chain == ("Base64", "Hex")
    )
    assert chain_candidate.decoded == "hello"


def test_base64_then_rot13() -> None:
    encoded = base64.b64encode(b"uryyb").decode()  # "hello" rot13
    candidates = decode_candidates(encoded, max_depth=3)
    assert any(
        candidate.chain == ("Base64", "ROT13") and candidate.decoded == "hello"
        for candidate in candidates
    )


def test_depth_limit_respected() -> None:
    encoded = base64.b64encode(b"hello").decode()
    candidates = decode_candidates(encoded, max_depth=1)
    assert all(candidate.depth == 1 for candidate in candidates)


def test_cycle_detection_terminates() -> None:
    # ROT13(ROT13(x)) == x; the search must not loop forever.
    candidates = decode_candidates("hello", max_depth=10)
    assert all(candidate.depth <= 10 for candidate in candidates)
    assert len(candidates) <= 200


def test_gzip_chain() -> None:
    import gzip

    payload = gzip.compress(b"secret")
    encoded = base64.b64encode(payload).decode()
    candidates = decode_candidates(encoded, max_depth=2)
    assert any(
        candidate.name == "Base64→Gzip" and candidate.decoded == "secret"
        for candidate in candidates
    )


def test_invalid_data_yields_no_crash() -> None:
    candidates = decode_candidates("!!!not-anything@@@", max_depth=5)
    assert isinstance(candidates, list)
