"""Windows-specific read-only helpers (registry and startup paths)."""

from __future__ import annotations

import os
import re
import winreg
from pathlib import Path

REGISTRY_ROOTS = {
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
}

STARTUP_KEYS = (
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
    ("HKLM", r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ("HKLM", r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
)


def read_registry_values(
    root_name: str,
    sub_key: str,
) -> tuple[list[tuple[str, str]], list[str]]:
    """Read values from a registry key with KEY_READ only; returns (values, errors)."""
    root = REGISTRY_ROOTS.get(root_name)
    if root is None:
        return [], [f"未知注册表根：{root_name}"]
    values: list[tuple[str, str]] = []
    errors: list[str] = []
    try:
        with winreg.OpenKey(root, sub_key, 0, winreg.KEY_READ) as key:
            index = 0
            while True:
                try:
                    name, value, _value_type = winreg.EnumValue(key, index)
                except OSError:
                    break
                values.append((name, str(value)))
                index += 1
    except FileNotFoundError:
        return [], []
    except OSError as exc:
        errors.append(f"{root_name}\\{sub_key}: {exc}")
    return values, errors


def startup_folder_paths() -> list[tuple[str, Path]]:
    """Return (label, path) for the user and common startup folders."""
    folders: list[tuple[str, Path]] = []
    appdata = os.environ.get("APPDATA")
    programdata = os.environ.get("PROGRAMDATA")
    if appdata:
        folders.append(
            (
                "用户 Startup 目录",
                Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
            )
        )
    if programdata:
        folders.append(
            (
                "公共 Startup 目录",
                Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
            )
        )
    return folders


_QUOTED_PATH = re.compile(r'^"([^"]+)"')


def command_executable_path(command: str) -> str | None:
    """Extract the first token of a startup command as an executable path."""
    stripped = command.strip()
    if not stripped:
        return None
    quoted = _QUOTED_PATH.match(stripped)
    if quoted:
        return quoted.group(1)
    token = stripped.split(" ", 1)[0]
    if "%" in token or not token:
        return None
    return token


def command_has_script_host(command: str) -> bool:
    lowered = command.lower()
    return any(
        keyword in lowered
        for keyword in ("powershell", "wscript", "cscript", "mshta", "cmd.exe /c", "cmd /c")
    )
