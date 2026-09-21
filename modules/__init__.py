"""Security tool modules, grouped by category.

Each tool implements the :class:`core.tool_definition.BaseTool` contract and is
discovered through the :class:`core.tool_registry.ToolRegistry`. Tools never touch
the UI layer directly.
"""

from __future__ import annotations

from core.tool_registry import ToolRegistry


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Register every built-in tool shipped with the application."""
    from modules.crypto.md5_reverse import MD5ReverseCtfTool, MD5ReverseTool
    from modules.network.dns import DnsTool
    from modules.network.ip_info import IPInfoTool
    from modules.network.network_interfaces import NetworkInterfacesTool
    from modules.network.ping import PingTool
    from modules.network.tcp_connect import TCPConnectTool
    from modules.network.tcp_scan import TcpScanTool

    registry.register(IPInfoTool())
    registry.register(PingTool())
    registry.register(TCPConnectTool())
    registry.register(TcpScanTool())
    registry.register(DnsTool())
    registry.register(NetworkInterfacesTool())
    registry.register(MD5ReverseTool())
    registry.register(MD5ReverseCtfTool())


__all__ = ["register_builtin_tools"]
