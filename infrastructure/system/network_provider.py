"""Network interface enumeration based on psutil."""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import DependencyMissingError


@dataclass(frozen=True, slots=True)
class InterfaceInfo:
    """Normalized view of one network interface."""

    name: str
    mac: str | None = None
    ipv4: tuple[str, ...] = ()
    ipv6: tuple[str, ...] = ()
    up: bool = False
    mtu: int | None = None
    bytes_sent: int | None = None
    bytes_recv: int | None = None
    packets_sent: int | None = None
    packets_recv: int | None = None


class NetworkInterfaceProvider:
    """Reads interface configuration and counters through psutil."""

    def list_interfaces(self) -> list[InterfaceInfo]:
        try:
            import psutil
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise DependencyMissingError(
                "psutil is not installed",
                user_message="缺少系统信息依赖，请安装：pip install -e '.[system]'",
            ) from exc
        addresses = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        counters = psutil.net_io_counters(pernic=True)
        interfaces: list[InterfaceInfo] = []
        for name in addresses:
            info = stats.get(name)
            counter = counters.get(name)
            ipv4: list[str] = []
            ipv6: list[str] = []
            mac: str | None = None
            for address in addresses[name]:
                if address.family == 2:  # AF_INET
                    ipv4.append(address.address)
                elif address.family in (10, 23):  # AF_INET6 (Windows: 23)
                    ipv6.append(address.address.split("%")[0])
                elif address.family in (17, 6):  # AF_LINK / AF_PACKET
                    mac = address.address
            interfaces.append(
                InterfaceInfo(
                    name=name,
                    mac=mac,
                    ipv4=tuple(ipv4),
                    ipv6=tuple(ipv6),
                    up=bool(info.isup) if info is not None else False,
                    mtu=int(info.mtu) if info is not None and info.mtu else None,
                    bytes_sent=int(counter.bytes_sent) if counter is not None else None,
                    bytes_recv=int(counter.bytes_recv) if counter is not None else None,
                    packets_sent=int(counter.packets_sent) if counter is not None else None,
                    packets_recv=int(counter.packets_recv) if counter is not None else None,
                )
            )
        return sorted(interfaces, key=lambda item: item.name)
