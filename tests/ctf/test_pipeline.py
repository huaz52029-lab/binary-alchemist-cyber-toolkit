"""Pipeline save/execute behaviors."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from core.result import ResultStatus
from core.task import ExecutionContext
from core.tool_registry import ToolRegistry
from modules import register_builtin_tools
from modules.ctf.pipeline import PipelineTool
from modules.ctf.workspace.store import WorkspaceStore


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-pipe",
        tool_id="ctf.pipeline",
        logger=logging.getLogger("tests.pipe"),
        cancel_event=threading.Event(),
    )


def _tool(registry: ToolRegistry, tmp_path: Path) -> PipelineTool:
    return PipelineTool(registry, store=WorkspaceStore(root=tmp_path / "ws"))


def test_pipeline_executes_base64_hex(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    pipeline = json.dumps(
        {
            "name": "b64-hex",
            "pipeline_version": 1,
            "steps": [
                {"tool": "encoding.base64", "params": {"operation": "decode"}},
                {"tool": "encoding.hex", "params": {"operation": "decode"}},
            ],
        }
    )
    import base64

    encoded = base64.b64encode(b"hello".hex().encode()).decode()
    result = _tool(registry, tmp_path).run(
        {"action": "execute", "pipeline_json": pipeline, "input": encoded},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert result.data[-1]["output"] == "hello"


def test_pipeline_unknown_tool_partial(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    pipeline = json.dumps(
        {
            "name": "bad",
            "pipeline_version": 1,
            "steps": [{"tool": "encoding.nope", "params": {}}],
        }
    )
    result = _tool(registry, tmp_path).run(
        {"action": "execute", "pipeline_json": pipeline, "input": "x"},
        _context(),
    )
    assert result.status is ResultStatus.PARTIAL
    assert "不存在" in result.summary


def test_pipeline_rejects_network_tools(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    pipeline = json.dumps(
        {
            "name": "net",
            "pipeline_version": 1,
            "steps": [{"tool": "network.ping", "params": {}}],
        }
    )
    result = _tool(registry, tmp_path).run(
        {"action": "execute", "pipeline_json": pipeline, "input": "x"},
        _context(),
    )
    assert result.status is ResultStatus.FAILED
    assert "网络工具" in result.summary


def test_pipeline_version_mismatch(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    pipeline = json.dumps(
        {
            "name": "v2",
            "pipeline_version": 2,
            "steps": [{"tool": "encoding.hex", "params": {}}],
        }
    )
    result = _tool(registry, tmp_path).run(
        {"action": "execute", "pipeline_json": pipeline, "input": "x"},
        _context(),
    )
    assert result.status is ResultStatus.FAILED
    assert "版本不支持" in result.summary


def test_pipeline_save_and_list(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    tool = _tool(registry, tmp_path)
    pipeline = json.dumps(
        {
            "name": "demo",
            "pipeline_version": 1,
            "steps": [{"tool": "encoding.rot13", "params": {"operation": "transform"}}],
        }
    )
    saved = tool.run(
        {"action": "save", "name": "demo", "pipeline_json": pipeline},
        _context(),
    )
    assert saved.status is ResultStatus.SUCCESS
    listed = tool.run({"action": "list"}, _context())
    assert any(row["tool"] == "demo.json" for row in listed.data)
