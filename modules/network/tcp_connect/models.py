"""Input and result models for the TCP connect tool."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TCPConnectInput(BaseModel):
    target: str = Field(min_length=1, max_length=255)
    port: int = Field(default=80, ge=1, le=65535)
    timeout: int = Field(default=3000, ge=100, le=10000)


class ConnectResult(BaseModel):
    target: str
    port: int
    family: str
    resolved_address: str
    status: str
    latency_ms: float | None = None
    error: str | None = None


DISPLAY_SPEC: dict[str, Any] = {
    "title": "TCP 连接检测结果",
    "sections": [
        {
            "title": "基本信息",
            "items": [
                {"field": "target", "label": "目标"},
                {"field": "port", "label": "端口"},
                {"field": "family", "label": "协议"},
                {"field": "resolved_address", "label": "解析地址"},
            ],
        },
        {
            "title": "检测结果",
            "items": [
                {
                    "field": "status",
                    "label": "状态",
                    "map": {
                        "OPEN": "开放",
                        "CLOSED": "关闭",
                        "TIMEOUT": "超时",
                        "ERROR": "错误",
                    },
                },
                {"field": "latency_ms", "label": "耗时(ms)"},
                {"field": "error", "label": "错误说明"},
            ],
        },
    ],
}
