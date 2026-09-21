"""Input and result models for the Ping tool."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PingInput(BaseModel):
    """Validated Ping parameters."""

    target: str = Field(min_length=1, max_length=255)
    count: int = Field(default=4, ge=1, le=10)
    timeout: int = Field(default=1000, ge=100, le=5000)


class PingResultReply(BaseModel):
    sequence: int
    status: str
    latency_ms: float | None = None
    error: str | None = None


class PingResult(BaseModel):
    """Aggregated Ping statistics."""

    target: str
    resolved_address: str
    sent: int
    received: int
    lost: int
    loss_percent: float
    min_latency_ms: float | None = None
    max_latency_ms: float | None = None
    avg_latency_ms: float | None = None
    replies: list[PingResultReply] = Field(default_factory=list)


DISPLAY_SPEC: dict[str, Any] = {
    "title": "Ping 测试结果",
    "table": {
        "columns": [
            {"field": "sequence", "label": "序号"},
            {"field": "status", "label": "状态"},
            {"field": "latency_ms", "label": "延迟(ms)"},
            {"field": "error", "label": "错误"},
        ]
    },
}
