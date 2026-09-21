"""Shannon entropy over byte counts."""

from __future__ import annotations

import math
from collections.abc import Iterable


def shannon_entropy(counts: Iterable[int], total: int | None = None) -> float:
    """H(X) = -Σ p(x)·log2(p(x)), in bits (0..8 for bytes)."""
    if total is None:
        total = sum(counts)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in counts:
        if count <= 0:
            continue
        probability = count / total
        entropy -= probability * math.log2(probability)
    return entropy


def entropy_from_bytes(data: bytes) -> float:
    counts = [0] * 256
    for byte in data:
        counts[byte] += 1
    return shannon_entropy(counts)
