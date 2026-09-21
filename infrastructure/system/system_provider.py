"""Read-only system information provider built on psutil and platform."""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.exceptions import DependencyMissingError


@dataclass(frozen=True, slots=True)
class DiskInfo:
    device: str
    mountpoint: str
    filesystem: str
    total: int
    used: int
    free: int
    percent: float


@dataclass(frozen=True, slots=True)
class MemoryInfo:
    total: int
    used: int
    available: int
    percent: float
    swap_total: int
    swap_used: int
    swap_percent: float


@dataclass(frozen=True, slots=True)
class SystemInfoData:
    os_name: str
    os_version: str
    os_build: str
    architecture: str
    machine: str
    hostname: str
    username: str
    python_version: str
    processor: str
    logical_cpus: int
    physical_cpus: int | None
    boot_time: str
    uptime_seconds: int
    disks: tuple[DiskInfo, ...] = field(default_factory=tuple)


def _import_psutil() -> Any:
    try:
        import psutil
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise DependencyMissingError(
            "psutil is not installed",
            user_message="缺少系统信息依赖，请安装：pip install -e '.[system]'",
        ) from exc
    return psutil


class SystemInfoProvider:
    """Collects static system facts with per-field N/A fallbacks."""

    def get_system_info(self) -> SystemInfoData:
        psutil = _import_psutil()
        boot_timestamp = getattr(psutil, "boot_time", lambda: 0.0)()
        try:
            uptime = max(0, int(datetime.now(UTC).timestamp() - boot_timestamp))
            boot_time = datetime.fromtimestamp(boot_timestamp, UTC).isoformat()
        except (OverflowError, OSError, ValueError):
            uptime = 0
            boot_time = "N/A"
        return SystemInfoData(
            os_name=platform.system() or "N/A",
            os_version=platform.release() or "N/A",
            os_build=getattr(platform, "version", lambda: "N/A")(),
            architecture=f"{platform.architecture()[0] or 'N/A'}",
            machine=platform.machine() or "N/A",
            hostname=platform.node() or "N/A",
            username=os.environ.get("USERNAME", os.environ.get("USER", "N/A")),
            python_version=sys.version.split()[0],
            processor=platform.processor() or "N/A",
            logical_cpus=os.cpu_count() or 0,
            physical_cpus=getattr(psutil, "cpu_count", lambda logical: None)(logical=False),
            boot_time=boot_time,
            uptime_seconds=uptime,
            disks=tuple(self.list_disks()),
        )

    def get_cpu_usage(self) -> float | None:
        try:
            return float(_import_psutil().cpu_percent(interval=0.2))
        except Exception:  # pragma: no cover - platform variance
            return None

    def get_memory(self) -> MemoryInfo:
        memory = _import_psutil().virtual_memory()
        swap = _import_psutil().swap_memory()
        return MemoryInfo(
            total=int(memory.total),
            used=int(memory.used),
            available=int(memory.available),
            percent=float(memory.percent),
            swap_total=int(swap.total),
            swap_used=int(swap.used),
            swap_percent=float(swap.percent),
        )

    def list_disks(self) -> list[DiskInfo]:
        psutil = _import_psutil()
        disks: list[DiskInfo] = []
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
            except OSError:
                continue
            disks.append(
                DiskInfo(
                    device=partition.device,
                    mountpoint=partition.mountpoint,
                    filesystem=partition.fstype or "N/A",
                    total=int(usage.total),
                    used=int(usage.used),
                    free=int(usage.free),
                    percent=float(usage.percent),
                )
            )
        return disks

    def get_net_counters(self) -> tuple[int, int]:
        """Return (bytes_sent, bytes_recv) totals."""
        counters = _import_psutil().net_io_counters()
        return int(counters.bytes_sent), int(counters.bytes_recv)
