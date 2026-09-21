from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.exceptions import ToolRegistryError
from core.tool_definition import ToolCategory, ToolDefinition
from core.tool_registry import ToolRegistry
from tests.conftest import DummyTool


def test_valid_definition(dummy_tool: DummyTool) -> None:
    assert dummy_tool.definition.id == "system.dummy"
    assert dummy_tool.definition.category.display_name == "系统安全"


def test_id_must_match_category_at_registry() -> None:
    definition = ToolDefinition(id="network.ping", name="Ping", category=ToolCategory.SYSTEM)
    tool = DummyTool()
    tool.__dict__["definition"] = definition
    with pytest.raises(ToolRegistryError):
        ToolRegistry().register(tool)


def test_id_must_be_namespaced() -> None:
    with pytest.raises(ValidationError):
        ToolDefinition(id="Ping", name="Ping", category=ToolCategory.NETWORK)


def test_version_must_be_semver_like() -> None:
    with pytest.raises(ValidationError):
        ToolDefinition(
            id="network.ping",
            name="Ping",
            category=ToolCategory.NETWORK,
            version="latest",
        )


def test_base_tool_properties(dummy_tool: DummyTool) -> None:
    assert dummy_tool.id == "system.dummy"
    assert dummy_tool.category is ToolCategory.SYSTEM
