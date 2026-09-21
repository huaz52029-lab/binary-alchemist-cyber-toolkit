"""Set-Cookie parsing with value masking (privacy by default)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CookieInfo:
    name: str
    value_masked: str
    secure: bool
    http_only: bool
    same_site: str | None
    domain: str | None
    path: str | None
    expires: str | None
    max_age: str | None


def _mask(value: str) -> str:
    return value[:3] + "***" if len(value) > 3 else "***"


def parse_set_cookie(header: str) -> CookieInfo:
    """Parse one Set-Cookie header into a masked, structured record."""
    parts = header.split(";")
    name, _, value = parts[0].strip().partition("=")
    attributes: dict[str, str | bool] = {}
    for attribute in parts[1:]:
        key, separator, item = attribute.strip().partition("=")
        if not key:
            continue
        attributes[key.lower()] = item if separator else True
    return CookieInfo(
        name=name.strip(),
        value_masked=_mask(value.strip()),
        secure="secure" in attributes,
        http_only="httponly" in attributes,
        same_site=str(attributes["samesite"]) if "samesite" in attributes else None,
        domain=str(attributes["domain"]) if "domain" in attributes else None,
        path=str(attributes["path"]) if "path" in attributes else None,
        expires=str(attributes["expires"]) if "expires" in attributes else None,
        max_age=str(attributes["max-age"]) if "max-age" in attributes else None,
    )


def mask_set_cookie(header: str) -> str:
    """Mask only the value part of a Set-Cookie header."""
    parts = header.split(";")
    name, separator, value = parts[0].strip().partition("=")
    head = f"{name}={_mask(value.strip())}" if separator else name
    return ";".join([head, *[part.strip() for part in parts[1:]]])
