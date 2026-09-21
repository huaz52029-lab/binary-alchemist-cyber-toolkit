"""PluginManager: lifecycle, enable/disable, state persistence and refresh."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.exceptions import PluginError
from core.plugin_loader import PluginLoader
from core.plugin_sdk.plugin_context import PluginConfigManager, PluginContext
from core.plugin_sdk.plugin_definition import PluginDefinition, PluginStatus
from core.task_manager import TaskManager
from core.tool_registry import ToolRegistry


@dataclass(slots=True)
class PluginState:
    definition: PluginDefinition | None
    path: Path
    status: PluginStatus
    tools: tuple[str, ...] = ()
    error: str | None = None
    enabled_override: bool | None = None


class PluginManager:
    """Lists, enables, disables and refreshes plugins on top of PluginLoader."""

    def __init__(
        self,
        registry: ToolRegistry,
        plugins_dir: Path,
        task_manager: TaskManager,
        *,
        state_path: Path | None = None,
        logger: logging.Logger | None = None,
        app_config: Any = None,
    ) -> None:
        self._registry = registry
        self._plugins_dir = Path(plugins_dir)
        self._task_manager = task_manager
        self._logger = logger or logging.getLogger("core.plugins")
        self._state_path = state_path or (self._plugins_dir.parent / "data" / "plugin_state.json")
        self._config_manager = PluginConfigManager(self._state_path.parent)
        self._app_config = app_config
        self._loader = PluginLoader(
            registry,
            plugins_dir,
            logger=self._logger,
            config_manager=self._config_manager,
        )
        self._states: dict[str, PluginState] = {}
        self._overrides = self._load_overrides()
        self.scan()

    @property
    def states(self) -> list[PluginState]:
        return list(self._states.values())

    @property
    def plugins_dir(self) -> Path:
        return self._plugins_dir

    def get(self, plugin_id: str) -> PluginState | None:
        return self._states.get(plugin_id)

    def scan(self) -> list[PluginState]:
        """Discover and validate metadata; reconcile with persisted overrides."""
        discovered: dict[str, PluginState] = {}
        for path in self._loader.discover():
            try:
                definition = self._loader.load_metadata(path)
                state = PluginState(
                    definition=definition,
                    path=path,
                    status=PluginStatus.DISCOVERED,
                    enabled_override=self._overrides.get(definition.id),
                )
            except PluginError as exc:
                state = PluginState(
                    definition=None,
                    path=path,
                    status=PluginStatus.FAILED,
                    error=exc.user_message,
                )
            discovered[state.definition.id if state.definition else state.path.name] = state
        self._states = discovered
        for state in self._states.values():
            if (
                state.status is PluginStatus.DISCOVERED
                and state.definition is not None
                and not self._is_enabled(state)
            ):
                state.status = PluginStatus.DISABLED
        return self.states

    def load_enabled(self) -> int:
        """Load every enabled plugin and register its tools."""
        loaded = 0
        for state in self.states:
            if state.status is not PluginStatus.DISCOVERED:
                continue
            enabled = self._is_enabled(state)
            if not enabled:
                state.status = PluginStatus.DISABLED
                continue
            self._activate(state)
            if state.status.value == PluginStatus.ENABLED.value:
                loaded += 1
        return loaded

    def enable(self, plugin_id: str) -> bool:
        state = self._states.get(plugin_id)
        if state is None or state.definition is None:
            return False
        self._overrides[plugin_id] = True
        self._persist_overrides()
        self._activate(state)
        return state.status is PluginStatus.ENABLED

    def disable(self, plugin_id: str) -> bool:
        state = self._states.get(plugin_id)
        if state is None:
            return False
        self._overrides[plugin_id] = False
        self._persist_overrides()
        self._deactivate(state)
        return True

    def refresh(self) -> int:
        """Rescan and re-activate enabled plugins."""
        for state in self._states.values():
            if state.status in (PluginStatus.ENABLED, PluginStatus.LOADED):
                self._deactivate(state)
        self.scan()
        return self.load_enabled()

    def _activate(self, state: PluginState) -> None:
        definition = state.definition
        if definition is None:
            return
        if state.status is PluginStatus.ENABLED:
            return
        state.status = PluginStatus.LOADING
        context = PluginContext(
            plugin_id=definition.id,
            plugin_root=state.path,
            logger=self._logger.getChild(definition.id),
            config_manager=self._config_manager,
            tool_registry=self._registry,
            task_manager=self._task_manager,
            app_config=self._app_config,
        )
        info = self._loader.load_plugin(state.path, context=context)
        if not info.loaded:
            state.status = PluginStatus.FAILED
            state.error = info.error
            return
        state.status = PluginStatus.ENABLED
        state.tools = info.tools
        state.error = None

    def _deactivate(self, state: PluginState) -> None:
        if state.status in (PluginStatus.ENABLED, PluginStatus.LOADED):
            state.status = PluginStatus.UNLOADING
            if state.definition is not None:
                self._loader.unload(state.definition.id)
        state.status = PluginStatus.DISABLED
        state.tools = ()

    def _is_enabled(self, state: PluginState) -> bool:
        if state.enabled_override is not None:
            return state.enabled_override
        return bool(state.definition and state.definition.enabled)

    def _load_overrides(self) -> dict[str, bool]:
        if not self._state_path.is_file():
            return {}
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            key: value["enabled"]
            for key, value in data.items()
            if isinstance(value, dict) and isinstance(value.get("enabled"), bool)
        }

    def _persist_overrides(self) -> None:
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                plugin_id: {"enabled": enabled} for plugin_id, enabled in self._overrides.items()
            }
            self._state_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:  # pragma: no cover - best effort
            self._logger.warning("Failed to persist plugin state: %s", exc)
