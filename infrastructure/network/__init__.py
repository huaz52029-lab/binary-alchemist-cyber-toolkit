"""Network adapters: TCP probing, ICMP ping, DNS and HTTP helpers.

Tools depend on these clients rather than importing ``socket``, ``subprocess`` or
third-party libraries directly.
"""

from infrastructure.network.dns_client import SUPPORTED_RECORD_TYPES, DnsClient, DnsRecordData
from infrastructure.network.http_client import (
    HttpClient,
    HttpResponse,
    RedirectHop,
    host_scope_note,
    normalize_web_url,
    redact_header_value,
)
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
from infrastructure.network.tls_client import TlsClient, TlsInfo

__all__ = [
    "SUPPORTED_RECORD_TYPES",
    "DnsClient",
    "DnsRecordData",
    "HttpClient",
    "HttpResponse",
    "PingProvider",
    "PingReply",
    "PingReplyStatus",
    "PingStats",
    "PortProbeResult",
    "ProbeStatus",
    "RedirectHop",
    "TcpClient",
    "TlsClient",
    "TlsInfo",
    "WindowsPingProvider",
    "build_stats",
    "classify_socket_error",
    "host_scope_note",
    "normalize_web_url",
    "redact_header_value",
]
