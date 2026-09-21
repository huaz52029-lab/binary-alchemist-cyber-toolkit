"""Plugin discovery, validation, namespacing and isolated loading.

Plugins live one level under the plugins directory, ship a ``plugin.json``
manifest and an entry module exposing either a ``register(context)`` function or
``BaseTool`` subclasses. Tool ids are namespaced with the plugin id so a plugin
can never override official tools. A broken plugin is isolated and reported.

Security note: plugin code runs in-process with the same privileges as the
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

from pydantic import ValidationError

from core.exceptions import PluginError, ToolRegistryError
from core.paths import data_root
from core.plugin_sdk.plugin_context import PluginConfigManager, PluginContext
from core.plugin_sdk.plugin_definition import PluginDefinition
from core.plugin_sdk.tool_adapter import NamespacedTool
from core.plugin_sdk.types import api_compatible
from core.tool_definition import BaseTool
from core.tool_registry import ToolRegistry


@dataclass(frozen=True, slots=True)
class PluginInfo:
    """Result of loading a single plugin."""

    id: str
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


def _check_dependencies(definition: PluginDefinition) -> list[str]:
    missing = [name for name in definition.dependencies if importlib.util.find_spec(name) is None]
    return missing


class PluginLoader:
    """Scans the plugins directory and registers tools found in valid plugins."""

    def __init__(
        self,
        registry: ToolRegistry,
        plugins_dir: Path,
        logger: logging.Logger | None = None,
        config_manager: PluginConfigManager | None = None,
    ) -> None:
        self._registry = registry
        self._plugins_dir = Path(plugins_dir)
        self._logger = logger or logging.getLogger("core.plugins")
        self._config_manager = config_manager or PluginConfigManager(data_root() / "data")

    def discover(self) -> list[Path]:
        """Return one-level plugin folders containing ``plugin.json``."""
        if not self._plugins_dir.is_dir():
            return []
        return sorted(
            path
            for path in self._plugins_dir.iterdir()
            if path.is_dir() and (path / "plugin.json").is_file()
        )

    def load_metadata(self, plugin_dir: Path) -> PluginDefinition:
        """Read and validate ``plugin.json``; unknown keys are ignored."""
        manifest_path = plugin_dir / "plugin.json"
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PluginError(
                f"cannot read plugin manifest {manifest_path}: {exc}",
                user_message="插件清单无法读取或不是有效的 JSON。",
            ) from exc
        if not isinstance(raw, dict):
            raise PluginError(
                "plugin manifest is not an object",
                user_message="插件清单格式错误。",
            )
        try:
            definition = PluginDefinition.model_validate(raw)
        except ValidationError as exc:
            raise PluginError(
                f"invalid plugin manifest {manifest_path}: {exc}",
                user_message="插件清单缺少必要字段或格式错误。",
            ) from exc
        return definition

    def load_plugin(
        self,
        plugin_dir: Path,
        *,
        context: PluginContext | None = None,
    ) -> PluginInfo:
        """Load one plugin folder and register its namespaced tools."""
        try:
            definition = self.load_metadata(plugin_dir)
        except PluginError as exc:
            self._logger.warning("Skipping plugin in %s: %s", plugin_dir, exc)
            return PluginInfo(
                id=plugin_dir.name,
                name=plugin_dir.name,
                version="?",
                description="",
                author="",
                path=plugin_dir,
                entry="",
                loaded=False,
                error=exc.user_message,
            )
        if not api_compatible(definition.api_version):
            message = "插件API版本与当前程序不兼容。"
            self._logger.warning(
                "Plugin %s api mismatch: %s", definition.id, definition.api_version
            )
            return self._failed(definition, plugin_dir, message)
        missing = _check_dependencies(definition)
        if missing:
            message = f"缺少依赖：{', '.join(missing)}（请手动安装，本程序不会自动安装）"
            self._logger.warning("Plugin %s missing dependencies: %s", definition.id, missing)
            return self._failed(definition, plugin_dir, message)
        try:
            module = self._import_entry(plugin_dir, definition)
        except PluginError as exc:
            self._logger.warning("Plugin '%s' failed to import: %s", definition.id, exc)
            return self._failed(definition, plugin_dir, exc.user_message)
        plugin_context = context or PluginContext(
            plugin_id=definition.id,
            plugin_root=plugin_dir,
            logger=self._logger.getChild(definition.id),
            config_manager=self._config_manager,
            tool_registry=self._registry,
        )
        tools = self._collect_tools(module, definition, plugin_context)
        registered: list[str] = []
        errors: list[str] = []
        for tool in tools:
            namespaced = NamespacedTool(definition.id, tool)
            try:
                self._registry.register(namespaced)
                registered.append(namespaced.id)
            except ToolRegistryError as exc:
                errors.append(f"{namespaced.id}: {exc.user_message}")
        if errors:
            self._logger.warning("Plugin '%s' tool errors: %s", definition.id, "; ".join(errors))
        if not registered:
            self._logger.warning("Plugin '%s' exported no tools", definition.id)
        self._logger.info("Plugin %s loaded with %d tools", definition.id, len(registered))
        return PluginInfo(
            id=definition.id,
            name=definition.name,
            version=definition.version,
            description=definition.description,
            author=definition.author,
            path=plugin_dir,
            entry=definition.entry_point,
            loaded=True,
            tools=tuple(registered),
            error="; ".join(errors) or None,
        )

    def load_all(self, *, context: PluginContext | None = None) -> PluginReport:
        """Load every discovered plugin and return a report."""
        return PluginReport(
            tuple(self.load_plugin(path, context=context) for path in self.discover())
        )

    def unload(self, plugin_id: str) -> int:
        """Unregister a plugin's tools; returns how many were removed."""
        removed = self._registry.unregister_plugin(plugin_id)
        self._logger.info("Plugin %s unloaded (%d tools)", plugin_id, len(removed))
        return len(removed)

    @staticmethod
    def _failed(
        definition: PluginDefinition,
        plugin_dir: Path,
        message: str,
    ) -> PluginInfo:
        return PluginInfo(
            id=definition.id,
            name=definition.name,
            version=definition.version,
            description=definition.description,
            author=definition.author,
            path=plugin_dir,
            entry=definition.entry_point,
            loaded=False,
            error=message,
        )

    @staticmethod
    def _import_entry(plugin_dir: Path, definition: PluginDefinition) -> Any:
        entry_path = (plugin_dir / definition.entry_point).resolve()
        root = plugin_dir.resolve()
        if not entry_path.is_relative_to(root) or not entry_path.is_file():
            raise PluginError(
                f"plugin entry {entry_path} not found",
                user_message=f"找不到插件 {definition.name} 的入口文件。",
            )
        module_name = f"toolkit_plugin_{definition.id.replace('-', '_').replace('.', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, entry_path)
        if spec is None or spec.loader is None:
            raise PluginError(
                f"cannot create import spec for {entry_path}",
                user_message=f"无法加载插件 {definition.name}。",
            )
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise PluginError(
                f"plugin '{definition.id}' raised during import: {exc}",
                user_message=f"插件 {definition.name} 加载时发生错误：{exc}",
            ) from exc
        return module

    @staticmethod
    def _collect_tools(
        module: Any,
        definition: PluginDefinition,
        context: PluginContext,
    ) -> list[BaseTool]:
        register = getattr(module, "register", None)
        if callable(register):
            result = register(context)
            if isinstance(result, list):
                return [tool for tool in result if isinstance(tool, BaseTool)]
        tools: list[BaseTool] = []
        for _, candidate in vars(module).items():
            if (
                inspect.isclass(candidate)
                and issubclass(candidate, BaseTool)
                and not inspect.isabstract(candidate)
            ):
                tools.append(candidate())
        return tools
