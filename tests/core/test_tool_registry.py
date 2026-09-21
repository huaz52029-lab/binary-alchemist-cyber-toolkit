from __future__ import annotations

import pytest

from core.exceptions import ToolRegistryError
from core.tool_definition import ToolCategory, ToolDefinition
from core.tool_registry import ToolRegistry
from tests.conftest import DummyTool


def test_register_get_and_length(dummy_tool: DummyTool) -> None:
    registry = ToolRegistry()
    definition = registry.register(dummy_tool)
    assert definition.id == "system.dummy"
    assert len(registry) == 1
    assert registry.get("system.dummy") is dummy_tool
    assert "system.dummy" in registry
    assert list(registry) == ["system.dummy"]


def test_duplicate_registration_rejected(dummy_tool: DummyTool) -> None:
    registry = ToolRegistry()
    registry.register(dummy_tool)
    with pytest.raises(ToolRegistryError):
        registry.register(dummy_tool)


def test_list_is_sorted_and_filtered(dummy_tool: DummyTool) -> None:
    registry = ToolRegistry()
    registry.register(dummy_tool)
    other = DummyTool()
    other.definition = ToolDefinition(
        id="network.other",
        name="Other",
        category=ToolCategory.NETWORK,
    )
    registry.register(other)
    assert [d.id for d in registry.list_tools()] == ["network.other", "system.dummy"]
    assert [d.id for d in registry.list_tools(category=ToolCategory.SYSTEM)] == ["system.dummy"]


def test_navigation_groups() -> None:
    registry = ToolRegistry()
    registry.register(DummyTool())
    groups = registry.navigation()
    assert len(groups) == 1
    assert groups[0].category is ToolCategory.SYSTEM
    assert groups[0].display_name == "系统安全"
    assert groups[0].tools[0].id == "system.dummy"


def test_unregister(dummy_tool: DummyTool) -> None:
    registry = ToolRegistry()
    registry.register(dummy_tool)
    assert registry.unregister("system.dummy")
    assert not registry.unregister("system.dummy")
    assert len(registry) == 0
