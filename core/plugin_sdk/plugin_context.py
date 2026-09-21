"""PluginContext: the only official way plugins reach core services."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from core.config_manager import AppConfig
from core.exceptions import FileSystemError
from core.task_manager import TaskManager
from core.tool_registry import ToolRegistry


class PluginConfigManager:
    """Per-plugin JSON configuration under ``data/plugins/<id>.json``."""

    def __init__(self, data_dir: Path) -> None:
        self._root = Path(data_dir) / "plugins"

    def load(self, plugin_id: str) -> dict[str, Any]:
        path = self._root / f"{plugin_id}.json"
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FileSystemError(str(exc), user_message="插件配置无法读取。") from exc
        return data if isinstance(data, dict) else {}

    def save(self, plugin_id: str, data: dict[str, Any]) -> Path:
        path = self._root / f"{plugin_id}.json"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise FileSystemError(str(exc), user_message="插件配置无法保存。") from exc
        return path


class PluginContext:
    """Bridges a plugin to logger/config/registry/task manager/app context."""

    def __init__(
        self,
        *,
        plugin_id: str,
        plugin_root: Path,
        logger: logging.Logger,
        config_manager: PluginConfigManager,
        tool_registry: ToolRegistry,
        task_manager: TaskManager | None = None,
        app_config: AppConfig | None = None,
        app_context: Any = None,
    ) -> None:
        self.plugin_id = plugin_id
        self.plugin_root = Path(plugin_root)
        self.logger = logger
        self.config_manager = config_manager
        self.tool_registry = tool_registry
        self.task_manager = task_manager
        self.app_config = app_config
        self.app_context = app_context

    def resource_path(self, relative: str) -> Path:
        """Resolve a path inside the plugin's resources directory."""
        candidate = (self.plugin_root / "resources" / relative).resolve()
        root = self.plugin_root.resolve()
        if not candidate.is_relative_to(root):
            raise FileSystemError(
                "resource path escapes plugin root",
                user_message="资源路径越界。",
            )
        return candidate

    def get_config(self) -> dict[str, Any]:
        return self.config_manager.load(self.plugin_id)

    def save_config(self, data: dict[str, Any]) -> Path:
        return self.config_manager.save(self.plugin_id, data)
