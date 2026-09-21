"""Full chain: UI-facing call -> registry -> TaskManager -> tool -> history -> exporter.

These tests exercise real tools over localhost fixtures and assert that the
result lands in both the task snapshot, the SQLite history and the exporters.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.app_context import AppContext
from core.task import TaskStatus
from infrastructure.network import HttpClient


def _run_chain(
    context: AppContext,
    tool_id: str,
    params: dict[str, Any],
) -> Any:
    tool = context.tool_registry.get(tool_id)
    assert tool is not None, f"tool not registered: {tool_id}"
    task_id = context.task_manager.submit_tool(tool, params, timeout=60)
    snapshot = context.task_manager.wait(task_id, timeout=60)
    assert snapshot.status is TaskStatus.COMPLETED
    assert snapshot.result is not None
    assert snapshot.result.is_ok
    record = context.history_manager.get(task_id)
    assert record is not None, "task was not persisted to history"
    assert record["tool_id"] == tool_id
    assert record["status"] == "COMPLETED"
    assert context.exporter_manager.to_string(snapshot.result, "json")
    assert context.exporter_manager.to_string(snapshot.result, "txt")
    assert context.exporter_manager.to_string(snapshot.result, "csv")
    return snapshot.result


def test_ip_info_chain(context: AppContext) -> None:
    result = _run_chain(context, "network.ip_info", {"input": "192.168.1.0/28"})
    assert result.data
    assert result.data[0]["version"] == "IPv4"


def test_tcp_connect_chain(context: AppContext, tcp_ports: tuple[int, int]) -> None:
    open_port, closed_port = tcp_ports
    opened = _run_chain(context, "network.tcp_connect", {"target": "127.0.0.1", "port": open_port})
    assert opened.data[0]["status"] == "OPEN"
    closed = _run_chain(
        context,
        "network.tcp_connect",
        {"target": "127.0.0.1", "port": closed_port},
    )
    assert closed.data[0]["status"] == "CLOSED"


def test_hash_chain(context: AppContext, tmp_path: Path) -> None:
    target = tmp_path / "data.bin"
    target.write_bytes(b"abcdef" * 1000)
    result = _run_chain(
        context,
        "crypto.hash",
        {"mode": "file", "file_path": str(target), "algorithm": "SHA256"},
    )
    assert any(row.get("algorithm") == "SHA256" for row in result.data)
    hex_digest = next(row for row in result.data if row.get("algorithm") == "SHA256")
    assert len(hex_digest.get("hash", "")) == 64


def test_file_info_chain(context: AppContext, tmp_path: Path) -> None:
    target = tmp_path / "样本.txt"
    target.write_text("hello 网安", encoding="utf-8")
    result = _run_chain(context, "file_analysis.file_info", {"file_path": str(target)})
    assert result.data
    assert result.data[0]["name"] == "样本.txt"


def test_web_headers_chain(context: AppContext, http_server: str) -> None:
    result = _run_chain(
        context,
        "web.http_headers",
        {"url": f"{http_server}/headers", "method": "HEAD"},
    )
    values = {row["header"].lower(): row["value"] for row in result.data}
    assert values["content-security-policy"] == "default-src 'self'"
    assert values["x-frame-options"] == "DENY"


def test_md5_reverse_chain(context: AppContext) -> None:
    result = _run_chain(
        context,
        "crypto.md5_reverse",
        {
            "mode": "verify",
            "target": "5d41402abc4b2a76b9719d911017c592",
            "candidate": "hello",
        },
    )
    assert result.data[0]["matched"] == "是"


def test_http_response_body_is_bounded(http_server: str) -> None:
    response = HttpClient().request(f"{http_server}/big", method="GET")
    assert response.status_code == 200
    assert response.body_truncated is True
    assert len(response.body or b"") <= 1024 * 1024
