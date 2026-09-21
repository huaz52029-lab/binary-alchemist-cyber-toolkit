"""DNS: record mapping, error translation and tool behavior (mocked resolver)."""

from __future__ import annotations

import logging
import threading
from typing import Any

import dns.exception
import dns.resolver
import pytest

from core.exceptions import NetworkError, ToolInputError
from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.network import DnsClient
from modules.network.dns import DnsTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-dns",
        tool_id="network.dns",
        logger=logging.getLogger("tests.dns"),
        cancel_event=threading.Event(),
    )


class _FakeRdType:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeRecord:
    def __init__(self, rrtype: str, ttl: int, **attrs: Any) -> None:
        self.rdtype = _FakeRdType(rrtype)
        self.ttl = ttl
        for key, value in attrs.items():
            setattr(self, key, value)


class _FakeAnswer:
    def __init__(self, qname: str, records: list[Any], ttl: int = 300) -> None:
        self.qname = qname
        self.ttl = ttl
        self._records = records

    def __iter__(self) -> Any:
        return iter(self._records)


class _FakeResolver:
    def __init__(self, records: list[Any], error: Exception | None) -> None:
        self.nameservers: list[str] = []
        self.timeout = 0.0
        self.lifetime = 0.0
        self._records = records
        self._error = error

    def resolve(self, name: str, rrtype: str) -> _FakeAnswer:
        if self._error is not None:
            raise self._error
        return _FakeAnswer(name, self._records)


def _install_resolver(
    monkeypatch: pytest.MonkeyPatch,
    records: list[Any] | None = None,
    error: Exception | None = None,
) -> None:
    monkeypatch.setattr(
        dns.resolver,
        "Resolver",
        lambda configure=True: _FakeResolver(records or [], error),
    )


def test_query_a_and_aaaa(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_resolver(
        monkeypatch,
        [_FakeRecord("A", 300, address="1.2.3.4")],
    )
    records = DnsClient().query("example.com", "A")
    assert len(records) == 1
    assert records[0].type == "A"
    assert records[0].ttl == 300
    assert records[0].fields["address"] == "1.2.3.4"


def test_query_mx(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_resolver(
        monkeypatch,
        [_FakeRecord("MX", 300, preference=10, exchange="mail.example.com.")],
    )
    records = DnsClient().query("example.com", "MX")
    assert records[0].fields["preference"] == 10
    assert records[0].fields["exchange"] == "mail.example.com."


def test_query_txt_joins_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_resolver(
        monkeypatch,
        [_FakeRecord("TXT", 300, strings=[b"hello", b" world"])],
    )
    records = DnsClient().query("example.com", "TXT")
    assert records[0].fields["text"] == "hello world"


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (dns.resolver.NXDOMAIN(), "域名不存在。"),
        (dns.resolver.NoAnswer(), "该记录类型没有应答。"),
        (dns.resolver.NoNameservers(), "无法连接任何 DNS 服务器。"),
        (dns.resolver.LifetimeTimeout(), "DNS 查询超时。"),
        (dns.exception.Timeout(), "DNS 查询超时。"),
    ],
)
def test_error_translation(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    message: str,
) -> None:
    _install_resolver(monkeypatch, error=error)
    with pytest.raises(NetworkError) as exc_info:
        DnsClient().query("example.com", "A")
    assert exc_info.value.user_message == message


def test_invalid_inputs() -> None:
    client = DnsClient()
    with pytest.raises(ToolInputError):
        client.query("  ", "A")
    with pytest.raises(ToolInputError):
        client.query("example.com", "SRV")


def test_tool_a_query(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_resolver(
        monkeypatch,
        [_FakeRecord("A", 300, address="8.8.8.8"), _FakeRecord("A", 300, address="8.8.4.4")],
    )
    result = DnsTool().run(
        {"domain": "example.com", "record_type": "A", "nameserver": ""},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert len(result.data) == 2
    assert result.data[0]["address"] == "8.8.8.8"
    labels = [column["label"] for column in result.metadata["display"]["table"]["columns"]]
    assert labels == ["域名", "类型", "地址", "TTL"]


def test_tool_mx_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_resolver(
        monkeypatch,
        [_FakeRecord("MX", 300, preference=10, exchange="mail.example.com.")],
    )
    result = DnsTool().run(
        {"domain": "example.com", "record_type": "MX", "nameserver": "1.1.1.1"},
        _context(),
    )
    labels = [column["label"] for column in result.metadata["display"]["table"]["columns"]]
    assert labels == ["域名", "类型", "优先级", "邮件服务器", "TTL"]


def test_tool_nxdomain_fails_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_resolver(monkeypatch, error=dns.resolver.NXDOMAIN())
    result = DnsTool().run(
        {"domain": "missing.example", "record_type": "A", "nameserver": ""},
        _context(),
    )
    assert result.status is ResultStatus.FAILED
    assert result.summary == "域名不存在。"
