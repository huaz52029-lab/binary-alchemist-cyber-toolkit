"""Pure IP/CIDR analysis built on the standard ``ipaddress`` module."""

from __future__ import annotations

import ipaddress
from typing import Literal

from core.exceptions import ToolInputError
from modules.network.ip_info.models import IPInfoResult

UNRECOGNIZED_MESSAGE = "无法识别该IP地址或网络格式。"
EMPTY_MESSAGE = "请输入IP地址或CIDR。"


def _interface_for(value: str) -> ipaddress.IPv4Interface | ipaddress.IPv6Interface:
    try:
        return ipaddress.ip_interface(value)
    except ValueError as exc:
        raise ToolInputError(
            f"unrecognized IP target: {value!r}",
            user_message=UNRECOGNIZED_MESSAGE,
        ) from exc


def _usable_ipv4_hosts(prefix_length: int, total_addresses: int) -> int:
    if prefix_length == 31:
        return 2  # RFC 3021 point-to-point: both addresses are usable
    if prefix_length >= 32:
        return 1
    return max(0, total_addresses - 2)


def _build_result(
    value: str,
    input_type: str,
    interface: ipaddress.IPv4Interface | ipaddress.IPv6Interface,
) -> IPInfoResult:
    network = interface.network
    is_ipv4 = interface.version == 4
    total_addresses = network.num_addresses
    if is_ipv4:
        usable_hosts = _usable_ipv4_hosts(network.prefixlen, total_addresses)
        broadcast_address = str(network.broadcast_address)
        netmask = str(network.netmask)
        compressed = None
        expanded = None
    else:
        usable_hosts = total_addresses
        broadcast_address = None
        netmask = None
        compressed = interface.ip.compressed
        expanded = interface.ip.exploded
    return IPInfoResult(
        input=value,
        input_type=input_type,
        address=str(interface.ip),
        version="IPv4" if is_ipv4 else "IPv6",
        compressed=compressed,
        expanded=expanded,
        network=str(network),
        network_address=str(network.network_address),
        broadcast_address=broadcast_address,
        netmask=netmask,
        prefix_length=network.prefixlen,
        total_addresses=total_addresses,
        usable_hosts=usable_hosts,
        private=network.is_private,
        global_=network.is_global,
        loopback=network.is_loopback,
        link_local=network.is_link_local,
        multicast=network.is_multicast,
        reserved=network.is_reserved,
        unspecified=network.is_unspecified,
    )


def analyze_ip(target: str) -> IPInfoResult:
    """Analyze a single IPv4/IPv6 address or CIDR block.

    A bare address is analyzed with host-route semantics (``/32`` or ``/128``);
    an input containing ``/`` is treated as an interface/CIDR and its host bits,
    when present, are preserved for display while the network is derived from the
    prefix.
    """
    value = target.strip()
    if not value:
        raise ToolInputError("empty target", user_message=EMPTY_MESSAGE)
    input_type: Literal["address", "network"] = "network" if "/" in value else "address"
    interface = _interface_for(value)
    return _build_result(value, input_type, interface)
