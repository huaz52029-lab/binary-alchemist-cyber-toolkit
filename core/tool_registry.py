"""Central registry that discovers tools and drives navigation generation.

The UI never hard-codes tool entries: it asks the registry for the current
categories and definitions. Tools are registered with their :class:`BaseTool`
instance; metadata (id, name, icon, ...) comes from the associated
:class:`ToolDefinition`.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator

from pydantic import BaseModel

from core.exceptions import ToolRegistryError
from core.tool_definition import BaseTool, ToolCategory, ToolDefinition


class NavigationGroup(BaseModel):
    """A category plus its enabled tools, ready for the navigation widget."""

    category: ToolCategory
    display_name: str
    tools: list[ToolDefinition]


class ToolRegistry:
    """Thread-safe registry of available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._lock = threading.RLock()

    def register(self, tool: BaseTool) -> ToolDefinition:
        """Register a tool instance and return its definition.

        Raises :class:`ToolRegistryError` on duplicate or invalid ids.
        """
        definition = tool.definition
        with self._lock:
            if definition.id in self._tools:
                raise ToolRegistryError(
                    f"tool id '{definition.id}' is already registered",
                    user_message=f"工具 {definition.name} 已注册，跳过重复项。",
                )
            self._tools[definition.id] = tool
        return definition

    def unregister(self, tool_id: str) -> bool:
        """Remove a tool; returns whether it existed."""
        with self._lock:
            return self._tools.pop(tool_id, None) is not None

    def get(self, tool_id: str) -> BaseTool | None:
        """Return the registered tool instance, if any."""
        with self._lock:
            return self._tools.get(tool_id)

    def definition_of(self, tool_id: str) -> ToolDefinition | None:
        tool = self.get(tool_id)
        return tool.definition if tool is not None else None

    def list_tools(
        self,
        *,
        category: ToolCategory | None = None,
        include_disabled: bool = False,
    ) -> list[ToolDefinition]:
        """Return tool definitions, optionally filtered by category."""
        with self._lock:
            definitions = [tool.definition for tool in self._tools.values()]
        if category is not None:
            definitions = [d for d in definitions if d.category is category]
        if not include_disabled:
            definitions = [d for d in definitions if d.enabled]
        return sorted(definitions, key=lambda d: d.id)

    def categories(self) -> dict[ToolCategory, list[ToolDefinition]]:
        """Group enabled tools by category, preserving the enum order."""
        grouped: dict[ToolCategory, list[ToolDefinition]] = {}
        for definition in self.list_tools():
            grouped.setdefault(definition.category, []).append(definition)
        return grouped

    def navigation(self) -> list[NavigationGroup]:
        """Build the navigation structure consumed by the UI."""
        grouped = self.categories()
        return [
            NavigationGroup(
                category=category,
                display_name=category.display_name,
                tools=grouped[category],
            )
            for category in ToolCategory
            if category in grouped
        ]

    def __len__(self) -> int:
        with self._lock:
            return len(self._tools)

    def __contains__(self, tool_id: object) -> bool:
        return isinstance(tool_id, str) and tool_id in self._tools

    def __iter__(self) -> Iterator[str]:
        with self._lock:
            return iter(list(self._tools))
