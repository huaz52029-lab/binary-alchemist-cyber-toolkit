"""Local JWT structural parsing (decoder/analyzer, not exploitation)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from core.exceptions import ToolInputError
from infrastructure.crypto.base64url import base64url_decode


@dataclass(frozen=True, slots=True)
class JwtData:
    header: dict[str, Any]
    payload: dict[str, Any]
    signature: str
    header_json: str
    payload_json: str


def _decode_segment(value: str, label: str) -> dict[str, Any]:
    try:
        raw = base64url_decode(value).decode("utf-8")
        parsed = json.loads(raw)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ToolInputError(
            f"invalid JWT {label} segment",
            user_message=f"无法解析JWT {label}。",
        ) from exc
    if not isinstance(parsed, dict):
        raise ToolInputError(
            f"JWT {label} is not a JSON object",
            user_message=f"无法解析JWT {label}。",
        )
    return parsed


def parse_jwt(token: str) -> JwtData:
    """Split and decode a ``header.payload.signature`` token."""
    value = token.strip()
    parts = value.split(".")
    if len(parts) != 3:
        raise ToolInputError(
            f"JWT has {len(parts)} segments",
            user_message="JWT 格式错误：应为 header.payload.signature 三段。",
        )
    header_raw, payload_raw, signature = parts
    header = _decode_segment(header_raw, "Header")
    payload = _decode_segment(payload_raw, "Payload")
    return JwtData(
        header=header,
        payload=payload,
        signature=signature,
        header_json=json.dumps(header, ensure_ascii=False, indent=2),
        payload_json=json.dumps(payload, ensure_ascii=False, indent=2),
    )
