"""Target model and IP/CIDR helpers used by network-facing tools."""

from __future__ import annotations

import ipaddress
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, field_validator, model_validator

from core.exceptions import ToolInputError


class TargetType(StrEnum):
    """Coarse classification of a tool target."""

    IP_ADDRESS = "ip"
    HOSTNAME = "hostname"
    URL = "url"
    FILE = "file"
    UNKNOWN = "unknown"


def is_ip_address(value: str) -> bool:
    """Return whether *value* parses as an IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def is_private_address(value: str) -> bool:
    """Return whether *value* is a private (RFC 1918 / RFC 4193) address."""
    try:
        return ipaddress.ip_address(value).is_private
    except ValueError as exc:
        message = f"无效的 IP 地址：{value}"
        raise ToolInputError(message, user_message=message) from exc


def is_loopback_address(value: str) -> bool:
    """Return whether *value* is a loopback address."""
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError as exc:
        message = f"无效的 IP 地址：{value}"
        raise ToolInputError(message, user_message=message) from exc


def describe_cidr(value: str) -> dict[str, Any]:
    """Describe a CIDR block: network, broadcast, netmask and host range.

    Raises :class:`ToolInputError` when the value is not a valid CIDR block.
    """
    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError as exc:
        message = f"无效的 CIDR：{value}"
        raise ToolInputError(message, user_message=message) from exc

    is_ipv4 = network.version == 4
    if is_ipv4 and network.num_addresses >= 4:
        first_host = str(network.network_address + 1)
        last_host = str(network.broadcast_address - 1)
        host_count = network.num_addresses - 2
    else:
        first_host = str(network.network_address)
        last_host = str(network.broadcast_address)
        host_count = network.num_addresses if not is_ipv4 else 0
    return {
        "cidr": str(network),
        "network_address": str(network.network_address),
        "broadcast_address": str(network.broadcast_address),
        "netmask": str(network.netmask),
        "version": network.version,
        "host_count": host_count,
        "first_host": first_host,
        "last_host": last_host,
        "is_private": network.is_private,
    }


def _detect_type(value: str) -> TargetType:
    if is_ip_address(value):
        return TargetType.IP_ADDRESS
    if "://" in value:
        return TargetType.URL
    if "\\" in value or "/" in value:
        return TargetType.FILE
    return TargetType.HOSTNAME


class Target(BaseModel):
    """A validated analysis target."""

    value: str
    type: TargetType = TargetType.UNKNOWN

    @field_validator("value")
    @classmethod
    def _strip_value(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("target value must not be empty")
        return value

    @model_validator(mode="after")
    def _fill_type(self) -> Target:
        if self.type is TargetType.UNKNOWN:
            self.type = _detect_type(self.value)
        return self

    @property
    def is_ip(self) -> bool:
        """Whether the target is an IP address."""
        return is_ip_address(self.value)

    @property
    def is_private(self) -> bool:
        """Whether the target is a private IP address."""
        return self.is_ip and ipaddress.ip_address(self.value).is_private

    @property
    def is_loopback(self) -> bool:
        """Whether the target is a loopback address."""
        return self.is_ip and ipaddress.ip_address(self.value).is_loopback
