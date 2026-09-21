"""Network interfaces: provider mapping and tool behavior (psutil mocked)."""

from __future__ import annotations

import logging
import threading
from types import SimpleNamespace

import psutil
import pytest

from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.system import NetworkInterfaceProvider
from modules.network.network_interfaces import NetworkInterfacesTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-if",
        tool_id="network.interfaces",
        logger=logging.getLogger("tests.if"),
        cancel_event=threading.Event(),
    )


def _addr(family: int, address: str) -> SimpleNamespace:
    return SimpleNamespace(family=family, address=address)


def test_provider_maps_interfaces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        psutil,
        "net_if_addrs",
        lambda: {
            "Ethernet": [
                _addr(2, "192.168.1.100"),
                _addr(23, "fe80::1%12"),
                _addr(17, "aa:bb:cc:dd:ee:ff"),
            ],
            "Loop": [_addr(2, "127.0.0.1")],
            "Disabled": [_addr(2, "10.0.0.2")],
        },
    )
    monkeypatch.setattr(
        psutil,
        "net_if_stats",
        lambda: {
            "Ethernet": SimpleNamespace(isup=True, mtu=1500),
            "Loop": SimpleNamespace(isup=True, mtu=65536),
            "Disabled": SimpleNamespace(isup=False, mtu=1500),
        },
    )
    monkeypatch.setattr(
        psutil,
        "net_io_counters",
        lambda pernic=False: {
            "Ethernet": SimpleNamespace(
                bytes_sent=100,
                bytes_recv=200,
                packets_sent=1,
                packets_recv=2,
            )
        },
    )
    interfaces = NetworkInterfaceProvider().list_interfaces()
    assert [info.name for info in interfaces] == ["Disabled", "Ethernet", "Loop"]
    ethernet = interfaces[1]
    assert ethernet.ipv4 == ("192.168.1.100",)
    assert ethernet.ipv6 == ("fe80::1",)
    assert ethernet.mac == "aa:bb:cc:dd:ee:ff"
    assert ethernet.up is True
    assert ethernet.mtu == 1500
    assert ethernet.bytes_sent == 100
    loop = interfaces[2]
    assert loop.ipv6 == ()
    assert loop.mac is None
    assert interfaces[0].up is False


def test_tool_result_rows_and_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        psutil,
        "net_if_addrs",
        lambda: {"Ethernet": [_addr(2, "192.168.1.100"), _addr(17, "aa:bb:cc")], "Wifi": []},
    )
    monkeypatch.setattr(
        psutil,
        "net_if_stats",
        lambda: {
            "Ethernet": SimpleNamespace(isup=True, mtu=1500),
            "Wifi": SimpleNamespace(isup=False, mtu=1500),
        },
    )
    monkeypatch.setattr(psutil, "net_io_counters", lambda pernic=False: {})
    result = NetworkInterfacesTool().run({}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert len(result.data) == 2
    assert result.data[0]["status"] in ("UP", "DOWN")
    assert result.findings[0].title == "存在未启用的网络接口"
    labels = [column["label"] for column in result.metadata["display"]["table"]["columns"]]
    assert labels == ["接口", "IPv4", "IPv6", "MAC", "状态", "MTU"]


def test_provider_os_error_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> None:
        raise OSError("boom")

    monkeypatch.setattr(psutil, "net_if_addrs", fail)
    result = NetworkInterfacesTool().run({}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == "无法读取网络接口信息。"
