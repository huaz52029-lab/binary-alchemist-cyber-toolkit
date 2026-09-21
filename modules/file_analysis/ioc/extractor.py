"""Candidate IOC extraction from text (all results are candidates, never verdicts)."""

from __future__ import annotations

import ipaddress
import re

_IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6_PATTERN = re.compile(r"\b(?:[0-9a-fA-F]{0,4}:){2,}[0-9a-fA-F:]*\b")
_URL_PATTERN = re.compile(r"https?://[^\s'\"<>]+")
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_DOMAIN_PATTERN = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"(?:com|net|org|info|biz|io|co|cn|ru|de|uk|dev|app|xyz|me|top|cc|cloud)\b"
)
_WINDOWS_PATH_PATTERN = re.compile(r"\b[A-Za-z]:\\(?:[^\s'\"<>|*?]+\\?)+|\b\\\\[^\s'\"<>|]+\\.*")
_REGISTRY_PATTERN = re.compile(
    r"\b(?:HKEY_LOCAL_MACHINE|HKEY_CURRENT_USER|HKEY_CLASSES_ROOT|HKEY_USERS|"
    r"HKEY_CURRENT_CONFIG|HKLM|HKCU|HKCR|HKU|HKCC)\\?[^\s'\"<>|]+"
)


def _ipv4_note(value: str) -> str:
    address = ipaddress.ip_address(value)
    if address.is_unspecified:
        return "未指定地址"
    if address == ipaddress.ip_address("255.255.255.255"):
        return "受限广播地址"
    if address.is_private:
        return "私有地址"
    if address.is_loopback:
        return "回环地址"
    return "公网地址"


def _valid_ipv4(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return all(0 <= int(part) <= 255 for part in value.split("."))
    except ValueError:
        return False


def _valid_ipv6(value: str) -> bool:
    try:
        ipaddress.IPv6Address(value)
        return True
    except ValueError:
        return False


def _dedupe(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, str]] = []
    for row in rows:
        key = (row["type"], row["value"])
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def extract_iocs(text: str, context_size: int = 80) -> list[dict[str, str]]:
    """Extract candidate IOCs; everything is labeled as a candidate."""
    rows: list[dict[str, str]] = []

    def context(span: tuple[int, int]) -> str:
        start = max(0, span[0] - context_size // 2)
        return text[start : span[1] + context_size // 2].replace("\n", " ")

    for match in _URL_PATTERN.finditer(text):
        rows.append(
            {
                "type": "URL",
                "value": match.group(),
                "context": context(match.span()),
                "note": "候选",
            }
        )
    for match in _EMAIL_PATTERN.finditer(text):
        rows.append(
            {
                "type": "Email",
                "value": match.group(),
                "context": context(match.span()),
                "note": "候选",
            }
        )
    for match in _IPV4_PATTERN.finditer(text):
        value = match.group()
        if _valid_ipv4(value):
            rows.append(
                {
                    "type": "IPv4",
                    "value": value,
                    "context": context(match.span()),
                    "note": _ipv4_note(value),
                }
            )
    for match in _IPV6_PATTERN.finditer(text):
        value = match.group().rstrip(":")
        if _valid_ipv6(value) and ":" in value:
            rows.append(
                {"type": "IPv6", "value": value, "context": context(match.span()), "note": "候选"}
            )
    for match in _REGISTRY_PATTERN.finditer(text):
        rows.append(
            {
                "type": "Registry",
                "value": match.group(),
                "context": context(match.span()),
                "note": "候选",
            }
        )
    for match in _WINDOWS_PATH_PATTERN.finditer(text):
        rows.append(
            {
                "type": "WindowsPath",
                "value": match.group(),
                "context": context(match.span()),
                "note": "候选",
            }
        )
    for match in _DOMAIN_PATTERN.finditer(text):
        value = match.group()
        if not any(row["value"] == value for row in rows if row["type"] in ("URL", "Email")):
            rows.append(
                {
                    "type": "Domain",
                    "value": value,
                    "context": context(match.span()),
                    "note": "候选域名",
                }
            )
    return _dedupe(rows)
