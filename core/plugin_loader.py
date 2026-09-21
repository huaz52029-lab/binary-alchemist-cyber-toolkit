"""Plugin discovery, manifest validation and safe-ish loading.

Plugins are folders under the plugins directory containing a ``plugin.json``
manifest and an entry module that defines :class:`BaseTool` subclasses. A broken
plugin is isolated: its error is reported and the remaining plugins still load.

Security note: plugin code is executed in-process with the same privileges as the
application. Only install plugins you trust.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from core import APP_VERSION
from core.exceptions import PluginError, ToolRegistryError
from core.tool_definition import BaseTool
from core.tool_registry import ToolRegistry


class PluginManifest(BaseModel):
    """Validated plugin metadata read from ``plugin.json``."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    description: str = ""
    author: str = ""
    entry: str = Field(default="main", pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    min_app_version: str | None = None


@dataclass(frozen=True, slots=True)
class PluginInfo:
    """Result of loading a single plugin."""

    name: str
    version: str
    description: str
    author: str
    path: Path
    entry: str
    loaded: bool = False
    tools: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PluginReport:
    """Summary of a full plugin scan."""

    plugins: tuple[PluginInfo, ...] = ()

    @property
    def loaded_count(self) -> int:
        return sum(info.loaded for info in self.plugins)

    @property
    def failed_count(self) -> int:
        return sum(not info.loaded for info in self.plugins)


def _version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split(".")[:3])


class PluginLoader:
    """Scans the plugins directory and registers tools found in valid plugins."""

    def __init__(
        self,
        registry: ToolRegistry,
        plugins_dir: Path,
        logger: logging.Logger | None = None,
    ) -> None:
        self._registry = registry
        self._plugins_dir = Path(plugins_dir)
        self._logger = logger or logging.getLogger("core.plugins")

    def discover(self) -> list[Path]:
        """Return plugin folders (directories containing ``plugin.json``)."""
        if not self._plugins_dir.is_dir():
            return []
        return sorted(
            path
            for path in self._plugins_dir.iterdir()
            if path.is_dir() and (path / "plugin.json").is_file()
        )

    def load_plugin(self, plugin_dir: Path) -> PluginInfo:
        """Load one plugin folder and register its tools."""
        manifest_path = plugin_dir / "plugin.json"
        try:
            manifest = self._read_manifest(manifest_path)
        except PluginError as exc:
            self._logger.warning("Skipping plugin in %s: %s", plugin_dir, exc)
            return PluginInfo(
                name=plugin_dir.name,
                version="?",
                description="",
                author="",
                path=plugin_dir,
                entry="",
                loaded=False,
                error=exc.user_message,
            )
        try:
            module = self._import_entry(plugin_dir, manifest)
        except PluginError as exc:
            self._logger.warning("Plugin '%s' failed to import: %s", manifest.name, exc)
            return PluginInfo(
                name=manifest.name,
                version=manifest.version,
                description=manifest.description,
                author=manifest.author,
                path=plugin_dir,
                entry=manifest.entry,
                loaded=False,
                error=exc.user_message,
            )
        tools = self._collect_tools(module)
        registered: list[str] = []
        errors: list[str] = []
        for tool in tools:
            try:
                self._registry.register(tool)
                registered.append(tool.id)
            except ToolRegistryError as exc:
                errors.append(f"{tool.id}: {exc.user_message}")
        if errors:
            self._logger.warning("Plugin '%s' tool errors: %s", manifest.name, "; ".join(errors))
        if not registered:
            self._logger.warning("Plugin '%s' exported no tools", manifest.name)
        return PluginInfo(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            author=manifest.author,
            path=plugin_dir,
            entry=manifest.entry,
            loaded=True,
            tools=tuple(registered),
            error="; ".join(errors) or None,
        )

    def load_all(self) -> PluginReport:
        """Load every discovered plugin and return a report."""
        return PluginReport(tuple(self.load_plugin(path) for path in self.discover()))

    def _read_manifest(self, path: Path) -> PluginManifest:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PluginError(
                f"cannot read plugin manifest {path}: {exc}",
                user_message="插件清单无法读取或不是有效的 JSON。",
            ) from exc
        try:
            manifest = PluginManifest.model_validate(raw)
        except ValidationError as exc:
            raise PluginError(
                f"invalid plugin manifest {path}: {exc}",
                user_message="插件清单缺少必要字段或格式错误。",
            ) from exc
        if manifest.min_app_version and _version_tuple(manifest.min_app_version) > _version_tuple(
            APP_VERSION
        ):
            raise PluginError(
                f"plugin requires app >= {manifest.min_app_version}",
                user_message=f"插件 {manifest.name} 需要更高版本的应用。",
            )
        return manifest

    @staticmethod
    def _import_entry(plugin_dir: Path, manifest: PluginManifest) -> Any:
        entry_path = plugin_dir / f"{manifest.entry}.py"
        if not entry_path.is_file():
            raise PluginError(
                f"plugin entry {entry_path} not found",
                user_message=f"找不到插件 {manifest.name} 的入口文件。",
            )
        module_name = f"toolkit_plugin_{manifest.name.replace('-', '_').replace('.', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, entry_path)
        if spec is None or spec.loader is None:
            raise PluginError(
                f"cannot create import spec for {entry_path}",
                user_message=f"无法加载插件 {manifest.name}。",
            )
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise PluginError(
                f"plugin '{manifest.name}' raised during import: {exc}",
                user_message=f"插件 {manifest.name} 加载时发生错误。",
            ) from exc
        return module

    @staticmethod
    def _collect_tools(module: Any) -> list[BaseTool]:
        tools: list[BaseTool] = []
        for _, candidate in vars(module).items():
            if (
                inspect.isclass(candidate)
                and issubclass(candidate, BaseTool)
                and not inspect.isabstract(candidate)
            ):
                tools.append(candidate())
        return tools
