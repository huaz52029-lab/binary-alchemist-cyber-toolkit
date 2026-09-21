"""Security tool modules, grouped by category.

Each tool implements the :class:`core.tool_definition.BaseTool` contract and is
discovered through the :class:`core.tool_registry.ToolRegistry`. Tools never touch
the UI layer directly.
"""

from __future__ import annotations

from core.tool_registry import ToolRegistry


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Register every built-in tool shipped with the application."""
    from modules.crypto.hash import HashTool
    from modules.crypto.jwt import JwtTool
    from modules.crypto.md5_reverse import MD5ReverseCtfTool, MD5ReverseTool
    from modules.crypto.rsa_helper import RsaHelperTool
    from modules.crypto.xor import XorTool
    from modules.ctf.auto_decode import AutoDecodeTool
    from modules.encoding.base32 import Base32Tool
    from modules.encoding.base58 import Base58Tool
    from modules.encoding.base64 import Base64Tool
    from modules.encoding.binary import BinaryTool
    from modules.encoding.hex import HexTool
    from modules.encoding.html_entity import HtmlEntityTool
    from modules.encoding.rot13 import Rot13Tool
    from modules.encoding.rot47 import Rot47Tool
    from modules.encoding.unicode import UnicodeTool
    from modules.encoding.url import UrlTool
    from modules.network.dns import DnsTool
    from modules.network.ip_info import IPInfoTool
    from modules.network.network_interfaces import NetworkInterfacesTool
    from modules.network.ping import PingTool
    from modules.network.tcp_connect import TCPConnectTool
    from modules.network.tcp_scan import TcpScanTool
    from modules.web.cookie_analysis import CookieAnalysisTool
    from modules.web.http_analysis import HttpAnalysisTool
    from modules.web.http_headers import HttpHeadersTool
    from modules.web.security_headers import SecurityHeadersTool
    from modules.web.tls_info import TlsInfoTool
    from modules.web.url_parser import UrlParserTool

    registry.register(IPInfoTool())
    registry.register(PingTool())
    registry.register(TCPConnectTool())
    registry.register(TcpScanTool())
    registry.register(DnsTool())
    registry.register(NetworkInterfacesTool())
    registry.register(MD5ReverseTool())
    registry.register(MD5ReverseCtfTool())
    registry.register(Base64Tool())
    registry.register(Base32Tool())
    registry.register(Base58Tool())
    registry.register(HexTool())
    registry.register(BinaryTool())
    registry.register(UrlTool())
    registry.register(UnicodeTool())
    registry.register(Rot13Tool())
    registry.register(Rot47Tool())
    registry.register(HtmlEntityTool())
    registry.register(HashTool())
    registry.register(XorTool())
    registry.register(JwtTool())
    registry.register(RsaHelperTool())
    registry.register(AutoDecodeTool())
    registry.register(UrlParserTool())
    registry.register(HttpHeadersTool())
    registry.register(CookieAnalysisTool())
    registry.register(SecurityHeadersTool())
    registry.register(TlsInfoTool())
    registry.register(HttpAnalysisTool())


__all__ = ["register_builtin_tools"]
