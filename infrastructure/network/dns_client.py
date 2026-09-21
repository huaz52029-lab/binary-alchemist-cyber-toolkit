"""DNS resolution built on dnspython with friendly error translation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from core.exceptions import DependencyMissingError, NetworkError, ToolInputError

SUPPORTED_RECORD_TYPES = ("A", "AAAA", "CNAME", "MX", "NS", "TXT", "PTR", "SOA")


@dataclass(frozen=True, slots=True)
class DnsRecordData:
    """Type-agnostic DNS record with type-specific fields."""

    name: str
    type: str
    ttl: int
    fields: dict[str, Any] = field(default_factory=dict)


class DnsClient:
    """Queries DNS through dnspython and normalizes errors."""

    def __init__(self, *, default_timeout: float = 5.0, max_timeout: float = 10.0) -> None:
        self._default_timeout = default_timeout
        self._max_timeout = max_timeout
        self._logger = logging.getLogger("infra.network.dns")

    def query(
        self,
        name: str,
        rrtype: str,
        nameserver: str | None = None,
        timeout: float | None = None,
    ) -> list[DnsRecordData]:
        """Resolve *name* and return normalized records."""
        value = name.strip()
        if not value:
            raise ToolInputError("empty name", user_message="请输入要查询的域名。")
        if rrtype not in SUPPORTED_RECORD_TYPES:
            raise ToolInputError(f"unsupported rrtype: {rrtype}", user_message="不支持的记录类型。")
        try:
            import dns.exception
            import dns.name
            import dns.resolver
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise DependencyMissingError(
                "dnspython is not installed",
                user_message="缺少 DNS 依赖，请安装：pip install -e '.[network]'",
            ) from exc
        resolver = dns.resolver.Resolver(configure=nameserver is None)
        if nameserver:
            resolver.nameservers = [nameserver]
        effective = min(self._default_timeout if timeout is None else timeout, self._max_timeout)
        resolver.timeout = effective
        resolver.lifetime = effective
        try:
            answer = resolver.resolve(value, rrtype)
        except dns.resolver.NXDOMAIN as exc:
            raise NetworkError(f"NXDOMAIN: {value}", user_message="域名不存在。") from exc
        except dns.resolver.NoAnswer as exc:
            raise NetworkError(f"NoAnswer: {value}", user_message="该记录类型没有应答。") from exc
        except dns.resolver.NoNameservers as exc:
            raise NetworkError(
                f"NoNameservers: {value}", user_message="无法连接任何 DNS 服务器。"
            ) from exc
        except (dns.resolver.LifetimeTimeout, dns.exception.Timeout) as exc:
            raise NetworkError(f"DNS timeout: {value}", user_message="DNS 查询超时。") from exc
        except (dns.name.EmptyLabel, dns.name.LabelTooLong, dns.name.NameTooLong) as exc:
            raise NetworkError(f"invalid name: {value}", user_message="域名格式无效。") from exc
        except dns.exception.DNSException as exc:
            self._logger.warning("DNS query failed: %s %s -> %s", value, rrtype, exc)
            raise NetworkError(f"DNS failure: {value}", user_message="DNS 查询失败。") from exc
        return [self._to_record(answer, record) for record in answer]

    @staticmethod
    def _to_record(answer: Any, record: Any) -> DnsRecordData:
        rrtype = record.rdtype.name
        ttl = int(record.ttl) if record.ttl is not None else int(answer.ttl or 0)
        name = str(answer.qname)
        fields: dict[str, Any] = {}
        if rrtype in ("A", "AAAA"):
            fields["address"] = str(record.address)
        elif rrtype == "CNAME":
            fields["target"] = str(record.target)
        elif rrtype == "MX":
            fields["preference"] = int(record.preference)
            fields["exchange"] = str(record.exchange)
        elif rrtype in ("NS", "PTR"):
            fields["target"] = str(record.target)
        elif rrtype == "TXT":
            fields["text"] = "".join(
                part.decode("utf-8", errors="replace") for part in record.strings
            )
        elif rrtype == "SOA":
            fields.update(
                {
                    "mname": str(record.mname),
                    "rname": str(record.rname),
                    "serial": int(record.serial),
                    "refresh": int(record.refresh),
                    "retry": int(record.retry),
                    "expire": int(record.expire),
                    "minimum": int(record.minimum),
                }
            )
        return DnsRecordData(name=name, type=rrtype, ttl=ttl, fields=fields)
