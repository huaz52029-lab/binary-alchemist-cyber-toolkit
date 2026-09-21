"""Read-only process enumeration with per-process error isolation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ProcessInfo:
    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    rss: int
    status: str
    created: str
    exe: str


@dataclass(frozen=True, slots=True)
class ProcessDetail:
    pid: int
    name: str
    username: str
    status: str
    created: str
    cpu_percent: float
    memory_percent: float
    rss: int
    num_threads: int
    exe: str
    cmdline: str
    cwd: str
    environment_count: int


def _safe(value: Any, fallback: str = "") -> str:
    try:
        return str(value) if value is not None else fallback
    except Exception:  # pragma: no cover - defensive
        return fallback


class ProcessProvider:
    """Lists processes; a single unreadable process never breaks the list."""

    def list_processes(self) -> tuple[list[ProcessInfo], int]:
        import psutil

        rows: list[ProcessInfo] = []
        denied = 0
        for process in psutil.process_iter(["pid", "name", "username"]):
            try:
                info = process.info
                with process.oneshot():
                    created_raw = process.create_time()
                    created = (
                        datetime.fromtimestamp(created_raw, UTC).isoformat()
                        if created_raw
                        else "N/A"
                    )
                    rows.append(
                        ProcessInfo(
                            pid=int(info["pid"]),
                            name=_safe(info["name"], "N/A"),
                            username=_safe(info["username"], "[无法读取]"),
                            cpu_percent=process.cpu_percent(interval=None) or 0.0,
                            memory_percent=process.memory_percent() or 0.0,
                            rss=int(process.memory_info().rss or 0),
                            status=_safe(process.status(), "N/A"),
                            created=created,
                            exe=_safe(process.exe(), "[无法读取]"),
                        )
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                denied += 1
            except Exception:  # pragma: no cover - defensive
                denied += 1
        return rows, denied

    def get_process_detail(self, pid: int) -> ProcessDetail | None:
        import psutil

        try:
            process = psutil.Process(pid)
            with process.oneshot():
                created_raw = process.create_time()
                created = (
                    datetime.fromtimestamp(created_raw, UTC).isoformat() if created_raw else "N/A"
                )
                return ProcessDetail(
                    pid=pid,
                    name=_safe(process.name(), "N/A"),
                    username=_safe(process.username(), "[无法读取]"),
                    status=_safe(process.status(), "N/A"),
                    created=created,
                    cpu_percent=process.cpu_percent(interval=None) or 0.0,
                    memory_percent=process.memory_percent() or 0.0,
                    rss=int(process.memory_info().rss or 0),
                    num_threads=process.num_threads() or 0,
                    exe=_safe(process.exe(), "[无法读取]"),
                    cmdline=_safe(" ".join(process.cmdline()), "[无法读取]"),
                    cwd=_safe(process.cwd(), "[无法读取]"),
                    environment_count=len(process.environ() or {}),
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None
        except Exception:  # pragma: no cover - defensive
            return None
