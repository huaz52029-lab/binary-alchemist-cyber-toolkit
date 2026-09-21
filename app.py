"""Application entry: argument handling and the headless core self-test.

In later phases this file gains the GUI launch path (QApplication + MainWindow);
the bootstrap stays here so ``main.py`` remains a thin shim.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from core import APP_DISPLAY_NAME, APP_NAME, APP_VERSION
from core.app_context import AppContext
from core.exceptions import TaskError
from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext, TaskStatus
from modules import register_builtin_tools


class Application:
    """Owns the application lifecycle from bootstrap to shutdown."""

    def __init__(self, context: AppContext, *, args: argparse.Namespace | None = None) -> None:
        self.context = context
        self._args = args or argparse.Namespace(self_test=False)
        self._logger = logging.getLogger("app")

    @classmethod
    def from_args(cls, argv: Sequence[str] | None = None) -> Application:
        parser = argparse.ArgumentParser(
            prog="cyber-toolkit",
            description=f"{APP_DISPLAY_NAME} - {APP_NAME}",
        )
        parser.add_argument(
            "--config",
            type=Path,
            help="path to the user configuration file",
        )
        parser.add_argument(
            "--home",
            type=Path,
            help="runtime data root (logs, data, plugins); overrides CYBERTOOLKIT_HOME",
        )
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default=None,
            help="override the configured log level",
        )
        parser.add_argument(
            "--plugins",
            action="store_true",
            help="load plugins from the plugins directory at startup",
        )
        parser.add_argument(
            "--self-test",
            action="store_true",
            help="run the core self-test and exit (default until the GUI lands)",
        )
        parser.add_argument(
            "--smoke-test",
            action="store_true",
            help="boot the full stack (GUI, registry, tasks, history, reports, plugins) "
            "and exit with a status",
        )
        parser.add_argument(
            "--version",
            action="version",
            version=f"{APP_NAME} {APP_VERSION}",
        )
        args = parser.parse_args(argv)
        context = AppContext.create(
            home=args.home,
            config_path=args.config,
            log_level=args.log_level,
            load_plugins=args.plugins,
        )
        register_builtin_tools(context.tool_registry)
        return cls(context, args=args)

    def run(self) -> int:
        """Run the application: GUI by default, self-test with ``--self-test``."""
        if self._args.self_test:
            try:
                self._run_self_test()
            finally:
                self.context.shutdown()
            return 0
        if self._args.smoke_test:
            return self._run_smoke_test()
        return self._run_gui()

    def _run_gui(self) -> int:
        try:
            from PySide6.QtWidgets import QApplication

            from ui.main_window import MainWindow
            from ui.theme import ThemeManager
        except ImportError:
            self._logger.error(
                "PySide6 is not installed; falling back to the self-test. "
                "Install it with: pip install -e '.[gui]'"
            )
            self._run_self_test()
            return 0
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationDisplayName(APP_DISPLAY_NAME)
        app.setApplicationVersion(APP_VERSION)
        try:
            theme_manager = ThemeManager(theme=self.context.config.theme)
            window = MainWindow(self.context, theme_manager)
            window.show()
            return app.exec()
        finally:
            self.context.shutdown()

    def _run_self_test(self) -> None:
        """Exercise the full core pipeline: registry -> tasks -> result -> export."""
        self._logger.info("Starting core self-test...")
        tools = self.context.tool_registry.list_tools()
        self._logger.info("Registered tools: %d", len(tools))

        task_id = self.context.task_manager.submit(
            "core.self_test",
            {},
            self._probe("self-test probe"),
        )
        snapshot = self.context.task_manager.wait(task_id, timeout=5.0)
        if (
            snapshot.status is not TaskStatus.COMPLETED
            or snapshot.result is None
            or not snapshot.result.is_ok
        ):
            raise TaskError(
                "self-test task did not complete successfully",
                user_message="核心自检失败：任务未能成功完成。",
            )
        exported = self.context.exporter_manager.to_string(snapshot.result, "json")
        if not exported:
            raise TaskError(
                "self-test export produced no output",
                user_message="核心自检失败：结果导出为空。",
            )
        self._logger.info(
            "Core self-test passed: status=%s duration=%.3fs",
            snapshot.result.status.value,
            snapshot.result.duration or 0.0,
        )

    def _run_smoke_test(self) -> int:
        """Boot every service plus the GUI and verify them end to end."""
        try:
            tool_count = len(self.context.tool_registry.list_tools())
            if tool_count == 0:
                raise TaskError(
                    "no tools registered",
                    user_message="冒烟测试失败：没有注册任何工具。",
                )
            self._logger.info("Smoke test: %d tools registered", tool_count)
            loaded = self.context.plugin_manager.load_enabled()
            self._logger.info(
                "Smoke test: %d plugins loaded, %d tools total",
                loaded,
                len(self.context.tool_registry.list_tools()),
            )
            self._logger.info("Smoke test: %d plugin states scanned", self.context.plugin_count())
            _rows, _total = self.context.history_manager.query(limit=1)
            report = self.context.report_manager.create("冒烟测试报告", template="basic")
            if not self.context.report_manager.render_markdown(report.report_id):
                raise TaskError(
                    "report render produced no markdown",
                    user_message="冒烟测试失败：报告渲染为空。",
                )
            task_id = self.context.task_manager.submit(
                "core.smoke_test",
                {},
                self._probe("smoke-test probe"),
            )
            snapshot = self.context.task_manager.wait(task_id, timeout=10.0)
            if snapshot.status is not TaskStatus.COMPLETED or snapshot.result is None:
                raise TaskError(
                    "smoke task did not complete",
                    user_message="冒烟测试失败：后台任务未能完成。",
                )
            self._smoke_gui()
            self._logger.info("Smoke test passed")
            return 0
        except Exception:
            self._logger.exception("Smoke test failed")
            return 1
        finally:
            self.context.shutdown()

    def _smoke_gui(self) -> None:
        """Construct the main window offscreen and pump one event-loop cycle."""
        try:
            from PySide6.QtWidgets import QApplication

            from ui.main_window import MainWindow
            from ui.theme import ThemeManager
        except ImportError as exc:
            raise TaskError(
                "PySide6 is not installed",
                user_message="冒烟测试失败：缺少 GUI 依赖。",
            ) from exc
        app = QApplication.instance() or QApplication(sys.argv)
        theme_manager = ThemeManager(theme=self.context.config.theme)
        window = MainWindow(self.context, theme_manager)
        window.show()
        app.processEvents()
        window.close()
        app.processEvents()

    def _probe(self, label: str) -> Callable[[ExecutionContext], ToolResult]:
        """Return a trivial cancellable task body used by the self/smoke tests."""

        def probe(context: ExecutionContext) -> ToolResult:
            context.info(f"{label} running")
            context.set_progress(50.0, "half way")
            context.raise_if_cancelled()
            return context.make_result(
                ResultStatus.SUCCESS,
                f"{label} completed",
                data=[{"checked": True}],
            )

        return probe
