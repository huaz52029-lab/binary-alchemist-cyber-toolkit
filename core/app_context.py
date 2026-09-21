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
from core.logger import LoggerManager
from core.paths import RuntimePaths
from core.plugin_loader import PluginLoader
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

    @classmethod
    def create(
        cls,
        *,
        home: Path | str | None = None,
        config_path: Path | str | None = None,
        log_level: str | None = None,
        load_plugins: bool = False,
    ) -> AppContext:
        """Bootstrap every core service and return a ready context."""
        paths = RuntimePaths.resolve(home)
        paths.ensure_runtime_dirs()
        user_config = Path(config_path) if config_path is not None else paths.user_config
        config_manager = ConfigManager(user_config, defaults_path=paths.default_config)
        config = config_manager.load()
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
        context = cls(
            paths=paths,
            config=config,
            config_manager=config_manager,
            logger=logger,
            tool_registry=tool_registry,
            task_manager=task_manager,
            exporter_manager=exporter_manager,
        )
        boot_logger = logger.get_logger("app")
        boot_logger.info("%s %s booted", APP_NAME, APP_VERSION)
        if load_plugins:
            report = PluginLoader(
                tool_registry,
                paths.plugins,
                logger.get_logger("core.plugins"),
            ).load_all()
            boot_logger.info(
                "Plugins scanned: %d loaded, %d failed",
                report.loaded_count,
                report.failed_count,
            )
        return context

    def shutdown(self) -> None:
        """Release background workers and logging handlers."""
        self.task_manager.shutdown(wait=False)
        self.logger.shutdown()
