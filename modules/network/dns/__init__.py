"""DNS query tool package."""

from modules.network.dns.models import DnsInput, DnsRecord, build_display_spec
from modules.network.dns.tool import DnsTool

__all__ = ["DnsInput", "DnsRecord", "DnsTool", "build_display_spec"]
