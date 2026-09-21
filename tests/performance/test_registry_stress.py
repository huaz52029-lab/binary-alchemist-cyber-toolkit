"""ToolRegistry stress: 500 tools, collisions and plugin filtering."""

from __future__ import annotations

import time

import pytest

from core.exceptions import ToolRegistryError
from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext
from core.tool_definition import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameters,
)
from core.tool_registry import ToolRegistry


class _StubTool(BaseTool):
    definition: ToolDefinition

    def __init__(self, tool_id: str, *, plugin_id: str | None = None) -> None:
        self.definition = ToolDefinition(
            id=tool_id,
            name=tool_id,
            category=ToolCategory.CTF,
            plugin_id=plugin_id,
        )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        return context.make_result(ResultStatus.SUCCESS, "ok")


def test_registry_handles_500_tools_quickly() -> None:
    registry = ToolRegistry()
    started = time.perf_counter()
    for index in range(500):
        registry.register(_StubTool(f"ctf.stress_{index:04d}"))
    elapsed = time.perf_counter() - started
    assert len(registry) == 500
    assert len(registry.list_tools()) == 500
    assert len(registry.list_tools(category=ToolCategory.CTF)) == 500
    assert len(registry.list_tools(category=ToolCategory.NETWORK)) == 0
    assert elapsed < 2.0


def test_duplicate_ids_are_rejected() -> None:
    registry = ToolRegistry()
    registry.register(_StubTool("ctf.dup"))
    with pytest.raises(ToolRegistryError):
        registry.register(_StubTool("ctf.dup"))
    assert len(registry) == 1


def test_plugin_filtering_and_removal() -> None:
    registry = ToolRegistry()
    for index in range(20):
        registry.register(_StubTool(f"ctf.core_{index:02d}"))
    for index in range(30):
        registry.register(_StubTool(f"ctf.plugin_{index:02d}", plugin_id="binaryalchemist.test"))
    assert len(registry.list_tools(plugin_id="binaryalchemist.test")) == 30
    removed = registry.unregister_plugin("binaryalchemist.test")
    assert removed == [f"ctf.plugin_{index:02d}" for index in range(30)]
    assert len(registry.list_tools(plugin_id="binaryalchemist.test")) == 0
    assert len(registry) == 20
