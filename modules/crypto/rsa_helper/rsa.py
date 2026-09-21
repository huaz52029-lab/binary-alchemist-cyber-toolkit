"""Pure RSA parameter relationship analysis (CTF helper)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from core.exceptions import ToolInputError


@dataclass(frozen=True, slots=True)
class RsaParameters:
    n: int | None
    e: int | None
    d: int | None
    p: int | None
    q: int | None


def parse_int_field(value: str, field: str) -> int | None:
    """Parse an optional decimal big integer field."""
    stripped = value.strip()
    if not stripped:
        return None
    if not stripped.isdecimal():
        raise ToolInputError(
            f"{field} is not a decimal integer",
            user_message=f"{field} 必须是十进制整数。",
        )
    return int(stripped)


def analyze_parameters(parameters: RsaParameters) -> dict[str, Any]:
    """Compute derived facts from the provided RSA parameters."""
    p = parameters.p
    q = parameters.q
    e = parameters.e
    d = parameters.d
    n = parameters.n
    result: dict[str, Any] = {
        "has_p": p is not None,
        "has_q": q is not None,
        "has_phi": p is not None and q is not None,
        "n_matches_pq": None,
        "phi": None,
        "gcd_e_phi": None,
        "d_computed": None,
        "d_verified": None,
    }
    if p is not None and q is not None:
        computed_n = p * q
        phi = (p - 1) * (q - 1)
        result["phi"] = phi
        if n is not None:
            result["n_matches_pq"] = n == computed_n
        if e is not None:
            gcd = math.gcd(e, phi)
            result["gcd_e_phi"] = gcd
            if gcd == 1:
                result["d_computed"] = pow(e, -1, phi)
        if e is not None and d is not None:
            result["d_verified"] = (e * d) % phi == 1
    return result
