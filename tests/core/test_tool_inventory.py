"""Release gate: every built-in tool has complete, unique metadata."""

from __future__ import annotations

from core.tool_registry import ToolRegistry
from modules import register_builtin_tools


def test_all_builtin_tools_have_complete_unique_metadata() -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    tools = registry.list_tools()
    assert len(tools) >= 50
    ids = [definition.id for definition in tools]
    assert len(ids) == len(set(ids)), "tool ids must be unique"
    for definition in tools:
        assert definition.name.strip(), f"{definition.id} missing name"
        assert definition.category.value, f"{definition.id} missing category"
        assert definition.version, f"{definition.id} missing version"
        assert definition.description.strip(), f"{definition.id} missing description"


def test_expected_categories_present() -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    categories = {definition.category.value for definition in registry.list_tools()}
    assert {
        "network",
        "web",
        "encoding",
        "crypto",
        "file_analysis",
        "system",
        "ctf",
    } <= categories
