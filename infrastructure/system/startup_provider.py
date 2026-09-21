"""Read-only startup entry enumeration (registry Run keys + startup folders)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from infrastructure.system.windows_provider import (
    STARTUP_KEYS,
    command_executable_path,
    read_registry_values,
    startup_folder_paths,
)


@dataclass(frozen=True, slots=True)
class StartupEntry:
    source: str
    name: str
    command: str
    user_scope: str
    exists: bool | None


class StartupProvider:
    """Lists startup entries; never modifies the registry or the folders."""

    def list_startup_entries(self) -> tuple[list[StartupEntry], list[str]]:
        entries: list[StartupEntry] = []
        errors: list[str] = []
        for root, sub_key in STARTUP_KEYS:
            values, key_errors = read_registry_values(root, sub_key)
            errors.extend(key_errors)
            source = f"{root} {sub_key.rsplit(chr(92), 1)[-1]}"
            for name, command in values:
                executable = command_executable_path(command)
                exists = Path(executable).is_file() if executable else None
                entries.append(
                    StartupEntry(
                        source=source,
                        name=name,
                        command=command,
                        user_scope="用户" if root == "HKCU" else "系统",
                        exists=exists,
                    )
                )
        for label, folder in startup_folder_paths():
            try:
                if not folder.is_dir():
                    continue
                for item in sorted(folder.iterdir()):
                    entries.append(
                        StartupEntry(
                            source=label,
                            name=item.name,
                            command=str(item),
                            user_scope="用户" if "用户" in label else "公共",
                            exists=item.is_file(),
                        )
                    )
            except OSError as exc:
                errors.append(f"{label}: {exc}")
        return entries, errors
