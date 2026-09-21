"""Public Plugin API surface.

Plugins import from here instead of reaching into internal modules. This SDK is a
facade over the stable core contracts, not a copy of the core.
"""

from core.plugin_sdk.plugin_context import PluginConfigManager, PluginContext
from core.plugin_sdk.plugin_definition import PluginDefinition, PluginStatus
from core.plugin_sdk.tool_adapter import NamespacedTool
from core.plugin_sdk.types import PLUGIN_API_VERSION, api_compatible, parse_version
from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext
from core.tool_definition import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolParameterKind,
    ToolParameters,
)

__all__ = [
    "PLUGIN_API_VERSION",
    "BaseTool",
    "ExecutionContext",
    "NamespacedTool",
    "PluginConfigManager",
    "PluginContext",
    "PluginDefinition",
    "PluginStatus",
    "ResultStatus",
    "ToolCategory",
    "ToolDefinition",
    "ToolParameter",
    "ToolParameterKind",
    "ToolParameters",
    "ToolResult",
    "api_compatible",
    "parse_version",
]
