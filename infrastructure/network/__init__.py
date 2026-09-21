"""Network adapters: TCP probing, ICMP ping, DNS and HTTP helpers.

Tools depend on these clients rather than importing ``socket``, ``subprocess`` or
third-party libraries directly.
"""

from infrastructure.network.dns_client import SUPPORTED_RECORD_TYPES, DnsClient, DnsRecordData
from infrastructure.network.ping_client import (
    PingProvider,
    PingReply,
    PingReplyStatus,
    PingStats,
    WindowsPingProvider,
    build_stats,
)
from infrastructure.network.socket_client import (
    PortProbeResult,
    ProbeStatus,
    TcpClient,
    classify_socket_error,
)

__all__ = [
    "SUPPORTED_RECORD_TYPES",
    "DnsClient",
    "DnsRecordData",
    "PingProvider",
    "PingReply",
    "PingReplyStatus",
    "PingStats",
    "PortProbeResult",
    "ProbeStatus",
    "TcpClient",
    "WindowsPingProvider",
    "build_stats",
    "classify_socket_error",
]
