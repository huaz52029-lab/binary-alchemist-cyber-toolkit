"""Input and result models for the DNS tool."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from infrastructure.network import SUPPORTED_RECORD_TYPES


class DnsInput(BaseModel):
    domain: str = Field(min_length=1, max_length=255)
    record_type: str = "A"
    nameserver: str = ""


class DnsRecord(BaseModel):
    name: str
    type: str
    ttl: int
    address: str | None = None
    target: str | None = None
    preference: int | None = None
    exchange: str | None = None
    text: str | None = None
    mname: str | None = None
    rname: str | None = None
    serial: int | None = None
    refresh: int | None = None
    retry: int | None = None
    expire: int | None = None
    minimum: int | None = None


_COLUMN_SPECS: dict[str, list[dict[str, str]]] = {
    "A": [
        {"field": "name", "label": "域名"},
        {"field": "type", "label": "类型"},
        {"field": "address", "label": "地址"},
        {"field": "ttl", "label": "TTL"},
    ],
    "AAAA": [
        {"field": "name", "label": "域名"},
        {"field": "type", "label": "类型"},
        {"field": "address", "label": "地址"},
        {"field": "ttl", "label": "TTL"},
    ],
    "CNAME": [
        {"field": "name", "label": "域名"},
        {"field": "type", "label": "类型"},
        {"field": "target", "label": "目标"},
        {"field": "ttl", "label": "TTL"},
    ],
    "NS": [
        {"field": "name", "label": "域名"},
        {"field": "type", "label": "类型"},
        {"field": "target", "label": "服务器"},
        {"field": "ttl", "label": "TTL"},
    ],
    "PTR": [
        {"field": "name", "label": "名称"},
        {"field": "type", "label": "类型"},
        {"field": "target", "label": "目标"},
        {"field": "ttl", "label": "TTL"},
    ],
    "MX": [
        {"field": "name", "label": "域名"},
        {"field": "type", "label": "类型"},
        {"field": "preference", "label": "优先级"},
        {"field": "exchange", "label": "邮件服务器"},
        {"field": "ttl", "label": "TTL"},
    ],
    "TXT": [
        {"field": "name", "label": "域名"},
        {"field": "type", "label": "类型"},
        {"field": "text", "label": "文本"},
        {"field": "ttl", "label": "TTL"},
    ],
    "SOA": [
        {"field": "name", "label": "域名"},
        {"field": "type", "label": "类型"},
        {"field": "mname", "label": "主服务器"},
        {"field": "rname", "label": "负责人"},
        {"field": "serial", "label": "序列号"},
        {"field": "ttl", "label": "TTL"},
    ],
}


def build_display_spec(record_type: str) -> dict[str, Any]:
    """Return the display spec for one record type (fallback to A columns)."""
    columns = _COLUMN_SPECS.get(record_type, _COLUMN_SPECS["A"])
    return {"title": f"DNS 查询结果（{record_type}）", "table": {"columns": columns}}


RECORD_TYPE_CHOICES = list(SUPPORTED_RECORD_TYPES)
