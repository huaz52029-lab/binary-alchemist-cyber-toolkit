"""NamespacedTool: prefixes plugin tool ids with the plugin namespace."""

from __future__ import annotations

from core.result import ToolResult
from core.task import ExecutionContext
from core.tool_definition import BaseTool, ToolParameters


class NamespacedTool(BaseTool):
    """Adapts a plugin tool so its registry id is ``<plugin_id>.<tool_id>``."""

    def __init__(self, plugin_id: str, tool: BaseTool) -> None:
        self._tool = tool
        self.__dict__["definition"] = tool.definition.model_copy(
            update={
                "id": f"{plugin_id}.{tool.definition.id}",
                "plugin_id": plugin_id,
            }
        )

    @property
    def wrapped_tool(self) -> BaseTool:
        return self._tool

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        return self._tool.run(params, context)
