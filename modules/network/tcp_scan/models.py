"""Input, result models and port parsing for the TCP scan tool."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from core.exceptions import ToolInputError

SERVICE_HINTS = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    6379: "Redis",
    8080: "HTTP-Alt",
}


def parse_ports(spec: str) -> list[int]:
    """Parse a single port (``80``) or an inclusive range (``80-443``)."""
    value = spec.strip()
    if not value:
        raise ToolInputError("empty ports spec", user_message="请输入端口，例如 80 或 80-443。")
    try:
        if "-" in value:
            parts = value.split("-")
            if len(parts) != 2:
                raise ValueError
            start, end = int(parts[0]), int(parts[1])
        else:
            start = end = int(value)
    except ValueError as exc:
        raise ToolInputError(
            f"invalid ports spec: {value!r}",
            user_message="端口格式无效，示例：80 或 80-443。",
        ) from exc
    if not 1 <= start <= 65535 or not 1 <= end <= 65535:
        raise ToolInputError("port out of range", user_message="端口必须在 1-65535 之间。")
    if start > end:
        raise ToolInputError("inverted range", user_message="端口范围起始值不能大于结束值。")
    return list(range(start, end + 1))


class PortScanInput(BaseModel):
    target: str = Field(min_length=1, max_length=255)
    ports: str = Field(min_length=1, max_length=64)
    timeout: int = Field(default=2500, ge=100, le=5000)
    concurrency: int = Field(default=64, ge=1, le=256)


class PortScanResultEntry(BaseModel):
    port: int
    status: str
    latency_ms: float | None = None
    service_hint: str | None = None
    error: str | None = None


class PortScanResult(BaseModel):
    target: str
    ports_spec: str
    port_count: int
    open_count: int
    closed_count: int
    timeout_count: int
    error_count: int
    duration: float


DISPLAY_SPEC: dict[str, Any] = {
    "title": "TCP 端口扫描结果",
    "table": {
        "columns": [
            {"field": "port", "label": "端口"},
            {"field": "status", "label": "状态"},
            {"field": "latency_ms", "label": "耗时(ms)"},
            {"field": "service_hint", "label": "常见服务"},
            {"field": "error", "label": "错误"},
        ]
    },
}
