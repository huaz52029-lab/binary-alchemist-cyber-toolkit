"""IP Information tool: analyzer, tool contract, registry and task integration."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

import pytest

from core.exceptions import ToolInputError
from core.exporters import ExportManager
from core.finding import Severity
from core.result import ResultStatus
from core.task import ExecutionContext, TaskStatus
from core.task_manager import TaskManager
from core.tool_registry import ToolRegistry
from modules import register_builtin_tools
from modules.network.ip_info import IPInfoTool, analyze_ip
from modules.network.ip_info.analyzer import EMPTY_MESSAGE, UNRECOGNIZED_MESSAGE


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-ipinfo",
        tool_id="network.ip_info",
        logger=logging.getLogger("tests.ip_info"),
        cancel_event=threading.Event(),
    )


ANALYZER_CASES = [
    (
        "192.168.1.100",
        {
            "version": "IPv4",
            "input_type": "address",
            "network": "192.168.1.100/32",
            "prefix_length": 32,
            "total_addresses": 1,
            "usable_hosts": 1,
            "private": True,
            "global": False,
            "loopback": False,
            "link_local": False,
            "multicast": False,
            "reserved": False,
            "unspecified": False,
            "broadcast_address": "192.168.1.100",
            "netmask": "255.255.255.255",
        },
    ),
    (
        "192.168.1.100/24",
        {
            "version": "IPv4",
            "input_type": "network",
            "network": "192.168.1.0/24",
            "network_address": "192.168.1.0",
            "broadcast_address": "192.168.1.255",
            "netmask": "255.255.255.0",
            "prefix_length": 24,
            "total_addresses": 256,
            "usable_hosts": 254,
            "private": True,
            "global": False,
        },
    ),
    ("10.0.0.1", {"private": True, "global": False}),
    ("172.16.1.1", {"private": True}),
    ("8.8.8.8", {"private": False, "global": True}),
    ("127.0.0.1", {"loopback": True}),
    ("169.254.1.1", {"link_local": True}),
    ("224.0.0.1", {"multicast": True}),
    ("0.0.0.0", {"unspecified": True, "multicast": False}),
    ("255.255.255.255", {"reserved": True, "multicast": False}),
    (
        "192.168.1.0/31",
        {"total_addresses": 2, "usable_hosts": 2, "prefix_length": 31},
    ),
    (
        "192.168.1.0/32",
        {"total_addresses": 1, "usable_hosts": 1, "prefix_length": 32},
    ),
    (
        "2001:db8::1",
        {
            "version": "IPv6",
            "compressed": "2001:db8::1",
            "expanded": "2001:0db8:0000:0000:0000:0000:0000:0001",
            "broadcast_address": None,
            "netmask": None,
            "prefix_length": 128,
            "total_addresses": 1,
            "usable_hosts": 1,
            "private": True,
            "global": False,
        },
    ),
    (
        "2001:db8::/64",
        {
            "input_type": "network",
            "network": "2001:db8::/64",
            "prefix_length": 64,
            "total_addresses": 2**64,
            "usable_hosts": 2**64,
            "broadcast_address": None,
        },
    ),
    ("::", {"unspecified": True, "reserved": True}),
    ("::1", {"loopback": True}),
    ("fe80::1", {"link_local": True}),
    ("ff02::1", {"multicast": True}),
]


@pytest.mark.parametrize("target,expected", ANALYZER_CASES)
def test_analyze_ip_attributes(target: str, expected: dict[str, object]) -> None:
    info = analyze_ip(target)
    dumped = info.model_dump(by_alias=True)
    for field, value in expected.items():
        assert dumped[field] == value


@pytest.mark.parametrize(
    "target",
    ["", "   ", "not-an-ip", "999.999.999.999", "192.168.1.1/99", "300.1.2.3"],
)
def test_analyze_invalid_input_raises_tool_input_error(target: str) -> None:
    with pytest.raises(ToolInputError):
        analyze_ip(target)


def test_tool_definition_metadata() -> None:
    tool = IPInfoTool()
    assert tool.id == "network.ip_info"
    assert tool.name == "IP 信息分析器"
    assert tool.definition.version == "1.0.0"


def test_run_returns_structured_success() -> None:
    result = IPInfoTool().run({"input": "192.168.1.100/24"}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["network"] == "192.168.1.0/24"
    assert result.data[0]["usable_hosts"] == 254
    assert result.metadata["tool_id"] == "network.ip_info"
    assert result.metadata["display"]["title"] == "IP 信息分析结果"
    assert "私有" in result.summary
    assert result.findings
    assert result.findings[0].severity is Severity.INFO


def test_run_public_address_summary() -> None:
    result = IPInfoTool().run({"input": "8.8.8.8"}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert "公网" in result.summary


def test_run_empty_input_fails_gracefully() -> None:
    result = IPInfoTool().run({"input": "   "}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == EMPTY_MESSAGE


def test_run_invalid_input_fails_gracefully() -> None:
    result = IPInfoTool().run({"input": "999.999.999.999"}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == UNRECOGNIZED_MESSAGE


def test_registry_discovers_tool() -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    assert registry.get("network.ip_info") is not None
    assert registry.definition_of("network.ip_info") is not None
    assert registry.list_tools()[0].id == "network.ip_info"


def test_task_manager_executes_tool() -> None:
    manager = TaskManager(max_workers=2)
    try:
        task_id = manager.submit_tool(IPInfoTool(), {"input": "fe80::1"})
        snapshot = manager.wait(task_id, timeout=5.0)
        assert snapshot.status is TaskStatus.COMPLETED
        assert snapshot.result is not None
        assert snapshot.result.status is ResultStatus.SUCCESS
        assert snapshot.result.data[0]["link_local"] is True
    finally:
        manager.shutdown(wait=True)


def test_result_exports_json_txt_csv(tmp_path: Path) -> None:
    result = IPInfoTool().run({"input": "192.168.1.0/24"}, _context())
    manager = ExportManager.with_defaults()
    exported = manager.export(result, tmp_path / "ip.json")
    payload = json.loads(exported.read_text(encoding="utf-8"))
    assert payload["status"] == "SUCCESS"
    assert payload["data"][0]["network"] == "192.168.1.0/24"
    assert "192.168.1.0/24" in manager.to_string(result, "txt")
    assert "network" in manager.to_string(result, "csv")
