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
    from modules.ctf.challenge_analyzer import ChallengeAnalyzerTool
    from modules.ctf.crypto_helper import CryptoHelperTool
    from modules.ctf.data_transform import DataTransformTool
    from modules.ctf.flag_tools import FlagToolsTool
    from modules.ctf.mod_math import ModMathTool
    from modules.ctf.notes import NotesTool
    from modules.ctf.pipeline import PipelineTool
    from modules.ctf.regex import RegexTool
    from modules.ctf.text_analysis import TextAnalysisTool
    from modules.ctf.workspace import WorkspaceTool
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
    from modules.file_analysis.analyzer import FileAnalyzerTool
    from modules.file_analysis.batch import BatchAnalysisTool
    from modules.file_analysis.entropy import FileEntropyTool
    from modules.file_analysis.file_info import FileInfoTool
    from modules.file_analysis.hashes import FileHashesTool
    from modules.file_analysis.hex_viewer import FileHexViewerTool
    from modules.file_analysis.ioc import FileIocTool
    from modules.file_analysis.pe_analysis import PeAnalysisTool
    from modules.file_analysis.strings import FileStringsTool
    from modules.network.dns import DnsTool
    from modules.network.ip_info import IPInfoTool
    from modules.network.network_interfaces import NetworkInterfacesTool
    from modules.network.ping import PingTool
    from modules.network.tcp_connect import TCPConnectTool
    from modules.network.tcp_scan import TcpScanTool
    from modules.system.analyzer import SystemAnalyzerTool
    from modules.system.connections import ConnectionsTool
    from modules.system.environment import EnvironmentTool
    from modules.system.process_detail import ProcessDetailTool
    from modules.system.processes import ProcessesTool
    from modules.system.resource_monitor import ResourceMonitorTool
    from modules.system.services import ServicesTool
    from modules.system.startup import StartupTool
    from modules.system.system_info import SystemInfoTool
    from modules.system.users import UsersTool
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
    registry.register(RegexTool())
    registry.register(FlagToolsTool())
    registry.register(TextAnalysisTool())
    registry.register(ModMathTool())
    registry.register(DataTransformTool())
    registry.register(ChallengeAnalyzerTool())
    registry.register(WorkspaceTool())
    registry.register(NotesTool())
    registry.register(PipelineTool(registry))
    registry.register(CryptoHelperTool(registry))
    registry.register(UrlParserTool())
    registry.register(HttpHeadersTool())
    registry.register(CookieAnalysisTool())
    registry.register(SecurityHeadersTool())
    registry.register(TlsInfoTool())
    registry.register(HttpAnalysisTool())
    registry.register(FileInfoTool())
    registry.register(FileHashesTool())
    registry.register(FileStringsTool())
    registry.register(FileEntropyTool())
    registry.register(FileHexViewerTool())
    registry.register(PeAnalysisTool())
    registry.register(FileIocTool())
    registry.register(FileAnalyzerTool())
    registry.register(BatchAnalysisTool())
    registry.register(SystemInfoTool())
    registry.register(ProcessesTool())
    registry.register(ProcessDetailTool())
    registry.register(ConnectionsTool())
    registry.register(ServicesTool())
    registry.register(StartupTool())
    registry.register(UsersTool())
    registry.register(EnvironmentTool())
    registry.register(ResourceMonitorTool())
    registry.register(SystemAnalyzerTool())


__all__ = ["register_builtin_tools"]
