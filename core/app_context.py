"""Application composition root.

``AppContext`` wires the core services together exactly once at startup. It is the
only place that constructs :class:`ConfigManager`, :class:`LoggerManager`,
:class:`ToolRegistry`, :class:`TaskManager` and the export pipeline; other layers
receive them through this object.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core import APP_NAME, APP_VERSION
from core.config_manager import AppConfig, ConfigManager
from core.exporters import ExportManager
from core.history.task_history import TaskHistoryManager
from core.logger import LoggerManager
from core.paths import RuntimePaths
from core.plugin_manager import PluginManager
from core.reports.report_manager import ReportManager
from core.reports.report_repository import ReportRepository
from core.task_manager import TaskManager
from core.tool_registry import ToolRegistry


@dataclass(slots=True)
class AppContext:
    """Shared services and configuration available to every layer."""

    paths: RuntimePaths
    config: AppConfig
    config_manager: ConfigManager
    logger: LoggerManager
    tool_registry: ToolRegistry
    task_manager: TaskManager
    exporter_manager: ExportManager
    plugin_manager: PluginManager
    history_manager: TaskHistoryManager
    report_manager: ReportManager

    @classmethod
    def create(
        cls,
        *,
        home: Path | str | None = None,
        config_path: Path | str | None = None,
        log_level: str | None = None,
        load_plugins: bool | None = None,
    ) -> AppContext:
        """Bootstrap every core service and return a ready context."""
        paths = RuntimePaths.resolve(home)
        paths.ensure_runtime_dirs()
        user_config = Path(config_path) if config_path is not None else paths.user_config
        config_manager = ConfigManager(user_config, defaults_path=paths.default_config)
        config = config_manager.load()
        load_plugins = config.startup.load_plugins if load_plugins is None else load_plugins
        logger = LoggerManager(
            paths.logs,
            level=log_level or config.logging.level,
            console=config.logging.console,
        )
        logger.setup()
        tool_registry = ToolRegistry()
        task_manager = TaskManager(
            max_workers=config.tasks.max_workers,
            default_timeout=config.tasks.default_timeout,
            logger=logger.get_logger("core.tasks"),
        )
        exporter_manager = ExportManager.with_defaults()
        plugin_manager = PluginManager(
            tool_registry,
            paths.plugins,
            task_manager,
            state_path=paths.data / "plugin_state.json",
            logger=logger.get_logger("core.plugins"),
            app_config=config,
        )
        history_manager = TaskHistoryManager(
            paths.data / "toolkit.db",
            paths.data / "results",
            tool_registry,
            logger.get_logger("core.history"),
        )
        report_manager = ReportManager(
            ReportRepository(paths.data / "toolkit.db"),
            history_manager,
        )
        task_manager.subscribe(history_manager.record_task)
        context = cls(
            paths=paths,
            config=config,
            config_manager=config_manager,
            logger=logger,
            tool_registry=tool_registry,
            task_manager=task_manager,
            exporter_manager=exporter_manager,
            plugin_manager=plugin_manager,
            history_manager=history_manager,
            report_manager=report_manager,
        )
        boot_logger = logger.get_logger("app")
        boot_logger.info("%s %s booted", APP_NAME, APP_VERSION)
        if load_plugins:
            loaded = plugin_manager.load_enabled()
            boot_logger.info("Plugins enabled: %d loaded", loaded)
        return context

    def plugin_count(self) -> int:
        """Count discovered plugin folders without loading them."""
        return len(self.plugin_manager.states)

    def shutdown(self) -> None:
        """Release background workers and logging handlers."""
        self.task_manager.shutdown(wait=False)
        self.history_manager.close()
        self.report_manager.close()
        self.logger.shutdown()
