"""Input and output models for the IP Information tool."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class IPInfoInput(BaseModel):
    """Validated tool input; the GUI passes parameters as a mapping."""

    target: str = Field(min_length=1, max_length=500)


class IPInfoResult(BaseModel):
    """Structured analysis result embedded in a ToolResult ``data`` row."""

    input: str
    input_type: Literal["address", "network"]
    address: str
    version: Literal["IPv4", "IPv6"]
    compressed: str | None = None
    expanded: str | None = None
    network: str
    network_address: str
    broadcast_address: str | None = None
    netmask: str | None = None
    prefix_length: int
    total_addresses: int
    usable_hosts: int
    private: bool
    # ``global`` is a Python keyword; keep the field as ``global_`` but serialize
    # it under the spec name via the serialization alias.
    global_: bool = Field(serialization_alias="global")
    loopback: bool
    link_local: bool
    multicast: bool
    reserved: bool
    unspecified: bool

    def display_spec(self) -> dict[str, Any]:
        """Describe how the UI renders this result (sections, labels, value maps).

        Fields whose value is ``None`` (e.g. IPv6 broadcast address) are skipped
        by the result panel.
        """
        sections: list[tuple[str, list[dict[str, Any]]]] = [
            (
                "基本信息",
                [
                    {"field": "address", "label": "地址"},
                    {"field": "version", "label": "版本"},
                    {
                        "field": "input_type",
                        "label": "输入类型",
                        "map": {"address": "单个地址", "network": "CIDR 网络"},
                    },
                ],
            ),
            (
                "网络信息",
                [
                    {"field": "network", "label": "网络"},
                    {"field": "network_address", "label": "网络地址"},
                    {"field": "broadcast_address", "label": "广播地址"},
                    {"field": "netmask", "label": "子网掩码"},
                    {"field": "prefix_length", "label": "前缀长度"},
                    {"field": "total_addresses", "label": "总地址数"},
                    {"field": "usable_hosts", "label": "可用主机数"},
                ],
            ),
            (
                "地址属性",
                [
                    {"field": "private", "label": "私有地址"},
                    {"field": "global", "label": "公网地址"},
                    {"field": "loopback", "label": "回环地址"},
                    {"field": "link_local", "label": "链路本地"},
                    {"field": "multicast", "label": "组播"},
                    {"field": "reserved", "label": "保留地址"},
                    {"field": "unspecified", "label": "未指定地址"},
                ],
            ),
        ]
        if self.version == "IPv6":
            sections.insert(
                1,
                (
                    "IPv6 专属",
                    [
                        {"field": "compressed", "label": "压缩形式"},
                        {"field": "expanded", "label": "展开形式"},
                    ],
                ),
            )
        return {
            "title": "IP 信息分析结果",
            "sections": [{"title": title, "items": items} for title, items in sections],
        }
