"""Read-only Windows service enumeration via pywin32."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.exceptions import DependencyMissingError

STATUS_LABELS = {
    1: "STOPPED",
    2: "START_PENDING",
    3: "STOP_PENDING",
    4: "RUNNING",
    5: "CONTINUE_PENDING",
    6: "PAUSE_PENDING",
    7: "PAUSED",
}

START_TYPE_LABELS = {
    0: "BOOT",
    1: "SYSTEM",
    2: "AUTO",
    3: "DEMAND",
    4: "DISABLED",
}


@dataclass(frozen=True, slots=True)
class ServiceInfo:
    name: str
    display_name: str
    status: str
    start_type: str
    account: str
    description: str
    binary_path: str


def _import_win32() -> tuple[Any, Any]:
    try:
        import win32con
        import win32service
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise DependencyMissingError(
            "pywin32 is not installed",
            user_message="缺少 Windows 服务依赖，请安装：pip install pywin32",
        ) from exc
    return win32con, win32service


class WindowsServiceProvider:
    """Enumerates services read-only; per-service failures never abort the list."""

    def list_services(self) -> tuple[list[ServiceInfo], list[str]]:
        win32con, win32service = _import_win32()
        services: list[ServiceInfo] = []
        errors: list[str] = []
        try:
            handle = win32service.OpenSCManager(None, None, win32con.SC_MANAGER_ENUMERATE_SERVICE)
        except Exception as exc:  # pragma: no cover - platform
            return [], [f"无法访问服务控制管理器：{exc}"]
        try:
            statuses = win32service.EnumServicesStatus(
                handle,
                win32con.SERVICE_WIN32,
                win32con.SERVICE_STATE_ALL,
            )
            for short_name, display_name, status in statuses:
                try:
                    config = self._query_config(win32service, short_name)
                    account, binary_path = config
                    description = self._query_description(win32service, win32con, short_name)
                    services.append(
                        ServiceInfo(
                            name=short_name,
                            display_name=display_name or short_name,
                            status=STATUS_LABELS.get(status[1], "UNKNOWN"),
                            start_type=START_TYPE_LABELS.get(
                                self._start_type(win32service, short_name), "UNKNOWN"
                            ),
                            account=account,
                            description=description,
                            binary_path=binary_path,
                        )
                    )
                except Exception as exc:  # pragma: no cover - permission variance
                    errors.append(f"{short_name}: {exc}")
        finally:
            win32service.CloseServiceHandle(handle)
        return services, errors

    @staticmethod
    def _query_config(win32service: Any, name: str) -> tuple[str, str]:
        handle = win32service.OpenService(None, name, win32service.SERVICE_QUERY_CONFIG)
        try:
            config = win32service.QueryServiceConfig(handle)
            return str(config[7] or "N/A"), str(config[3] or "")
        finally:
            win32service.CloseServiceHandle(handle)

    @staticmethod
    def _query_description(
        win32service: Any,
        win32con: Any,
        name: str,
    ) -> str:
        handle = win32service.OpenService(None, name, win32service.SERVICE_QUERY_CONFIG)
        try:
            description = win32service.QueryServiceConfig2(
                handle, win32con.SERVICE_CONFIG_DESCRIPTION
            )
            return str(description or "")
        finally:
            win32service.CloseServiceHandle(handle)

    @staticmethod
    def _start_type(win32service: Any, name: str) -> int:
        handle = win32service.OpenService(None, name, win32service.SERVICE_QUERY_CONFIG)
        try:
            return int(win32service.QueryServiceConfig(handle)[1])
        finally:
            win32service.CloseServiceHandle(handle)
