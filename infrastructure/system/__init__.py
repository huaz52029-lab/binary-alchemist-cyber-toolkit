"""System adapters: info, process, connection, service and Windows providers."""

from infrastructure.system.network_provider import (
    ConnectionInfo,
    ConnectionProvider,
    InterfaceInfo,
    NetworkInterfaceProvider,
)
from infrastructure.system.process_provider import (
    ProcessDetail,
    ProcessInfo,
    ProcessProvider,
)
from infrastructure.system.service_provider import ServiceInfo, WindowsServiceProvider
from infrastructure.system.startup_provider import StartupEntry, StartupProvider
from infrastructure.system.system_provider import (
    DiskInfo,
    MemoryInfo,
    SystemInfoData,
    SystemInfoProvider,
)

__all__ = [
    "ConnectionInfo",
    "ConnectionProvider",
    "DiskInfo",
    "InterfaceInfo",
    "MemoryInfo",
    "NetworkInterfaceProvider",
    "ProcessDetail",
    "ProcessInfo",
    "ProcessProvider",
    "ServiceInfo",
    "StartupEntry",
    "StartupProvider",
    "SystemInfoData",
    "SystemInfoProvider",
    "WindowsServiceProvider",
]
