"""Security tool modules, grouped by category.

Each tool implements the :class:`core.tool_definition.BaseTool` contract and is
discovered through the :class:`core.tool_registry.ToolRegistry`. Tools never touch
the UI layer directly.
"""

from __future__ import annotations

from core.tool_registry import ToolRegistry


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Register every built-in tool shipped with the application."""
    from modules.network.ip_info import IPInfoTool

    registry.register(IPInfoTool())


__all__ = ["register_builtin_tools"]
