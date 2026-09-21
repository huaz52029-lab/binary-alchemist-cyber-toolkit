"""Main application window: layout, page composition, navigation and lifecycle."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core import APP_DISPLAY_NAME, APP_VERSION
from core.app_context import AppContext
from core.config_manager import WindowSettings
from core.task import Task
from core.tool_definition import ToolCategory
from ui.bridge import LogBridge, TaskBridge
from ui.category_page import CategoryPage
from ui.dashboard import Dashboard
from ui.encoding_page import EncodingToolPage
from ui.history_page import TaskHistoryPage
from ui.icons import IconProvider
from ui.log_panel import LogPanel
from ui.navigation import (
    PAGE_DASHBOARD,
    PAGE_HISTORY,
    PAGE_PLUGINS,
    PAGE_REPORTS,
    PAGE_SETTINGS,
    Navigation,
)
from ui.plugin_page import PluginPage
from ui.report_page import ReportPage
from ui.settings_dialog import SettingsDialog
from ui.theme import ThemeManager
from ui.tool_page import ToolPage
from ui.widgets.command_input import CommandInput


class MainWindow(QMainWindow):
    """Composes header, navigation, content stack, log area and status bar.

    This class owns layout and lifecycle only. Tool execution, result routing and
    logging all flow through AppContext services and the signal bridges.
    """

    def __init__(
        self,
        context: AppContext,
        theme_manager: ThemeManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._context = context
        self._theme = theme_manager or ThemeManager(theme=context.config.theme)
        self._logger = logging.getLogger("ui.main")
        self._icons = IconProvider(context.paths.root / "resources" / "icons")
        self._tool_pages: dict[str, QWidget] = {}
        self._page_index: dict[str, int] = {}

        self.setWindowTitle(f"{APP_DISPLAY_NAME} · Cyber Toolkit")
        self.setMinimumSize(1024, 640)

        self._task_bridge = TaskBridge(context.task_manager, parent=self)
        self._log_bridge = LogBridge(parent=self)
        context.logger.attach_sink(self._log_bridge.handler)

        header = self._build_header()
        self._navigation = Navigation(context.tool_registry, icons=self._icons)
        self._stack = QStackedWidget(self)
        self._dashboard = Dashboard(context, self._theme)
        self._history_page = TaskHistoryPage(
            context.history_manager,
            self._theme,
            exporter_manager=context.exporter_manager,
        )
        self._history_page.re_run_requested.connect(self._re_run)
        self._report_page = ReportPage(context.report_manager)
        self._plugin_page = PluginPage(context.plugin_manager)
        self._plugin_page.open_tool_requested.connect(self._open_tool)
        pages: dict[str, QWidget] = {
            PAGE_DASHBOARD: self._dashboard,
            PAGE_HISTORY: self._history_page,
            PAGE_REPORTS: self._report_page,
            PAGE_PLUGINS: self._plugin_page,
        }
        for category in ToolCategory:
            category_page = CategoryPage(
                category,
                context.tool_registry.list_tools(category=category),
            )
            category_page.tool_selected.connect(self._open_tool)
            pages[category.value] = category_page
        for page_id, widget in pages.items():
            self._page_index[page_id] = self._stack.addWidget(widget)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self._navigation)
        splitter.addWidget(self._stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([240, 960])

        self._log_panel = LogPanel(self._theme, bridge=self._log_bridge)
        main_splitter = QSplitter(Qt.Orientation.Vertical, self)
        main_splitter.addWidget(splitter)
        main_splitter.addWidget(self._log_panel)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)
        main_splitter.setSizes([620, 160])

        central = QWidget(self)
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(header)
        central_layout.addWidget(main_splitter)
        self.setCentralWidget(central)

        self._build_status_bar()
        self._navigation.page_changed.connect(self._switch_page)
        self._navigation.tool_selected.connect(self._open_tool)
        self._task_bridge.task_created.connect(self._on_task_created)
        self._task_bridge.task_updated.connect(self._on_task_updated)
        self._task_bridge.task_finished.connect(self._on_task_finished)
        self._theme.theme_changed.connect(self._on_theme_changed)

        app = QApplication.instance()
        if isinstance(app, QApplication):
            self._theme.apply(app)
        self._navigation.select_page(PAGE_DASHBOARD)
        self._restore_geometry()

    def _build_header(self) -> QWidget:
        header = QWidget(self)
        header.setObjectName("header")
        title = QLabel(APP_DISPLAY_NAME, header)
        title.setObjectName("headerTitle")
        version = QLabel(f"v{APP_VERSION}", header)
        version.setObjectName("headerVersion")
        settings_button = QPushButton("设置", header)
        settings_button.setObjectName("flatButton")
        settings_button.setIcon(self._icons.icon("settings"))
        settings_button.clicked.connect(self._open_settings)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addStretch(1)
        layout.addWidget(settings_button)
        return header

    def _build_status_bar(self) -> None:
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        status_bar.showMessage("就绪")
        self._task_count_label = QLabel("任务：0", self)
        version_label = QLabel(f"v{APP_VERSION}", self)
        status_bar.addPermanentWidget(self._task_count_label)
        status_bar.addPermanentWidget(version_label)

    def _restore_geometry(self) -> None:
        window = self._context.config.window
        self.resize(window.width, window.height)
        if window.x is not None and window.y is not None:
            self.move(window.x, window.y)
        if window.maximized:
            self.showMaximized()

    def _switch_page(self, page_id: str) -> None:
        if page_id == PAGE_SETTINGS:
            self._open_settings()
            self._navigation.select_page(PAGE_DASHBOARD)
            return
        index = self._page_index.get(page_id)
        if index is None:
            self._logger.warning("Unknown page id: %s", page_id)
            return
        self._stack.setCurrentIndex(index)
        if page_id == PAGE_DASHBOARD:
            self._dashboard.refresh()
        if page_id == PAGE_PLUGINS:
            self._plugin_page.refresh()
        if page_id == PAGE_HISTORY:
            self._history_page.refresh()
        if page_id == PAGE_REPORTS:
            self._report_page.refresh()

    def _open_tool(self, tool_id: str) -> None:
        definition = self._context.tool_registry.definition_of(tool_id)
        if definition is None:
            self._logger.warning("Unknown tool id: %s", tool_id)
            return
        page = self._tool_pages.get(tool_id)
        if page is None:
            tool = self._context.tool_registry.get(tool_id)
            if definition.page == "encoding":
                page = EncodingToolPage(
                    definition,
                    self._theme,
                    self._log_bridge,
                    tool=tool,
                    task_manager=self._context.task_manager,
                    task_bridge=self._task_bridge,
                    exporter_manager=self._context.exporter_manager,
                )
            else:
                page = ToolPage(
                    definition,
                    self._theme,
                    self._log_bridge,
                    tool=tool,
                    task_manager=self._context.task_manager,
                    task_bridge=self._task_bridge,
                    exporter_manager=self._context.exporter_manager,
                )
                page.run_requested.connect(self._on_run_requested)
                page.send_to_requested.connect(self._send_to)
            self._stack.addWidget(page)
            self._tool_pages[tool_id] = page
        self._stack.setCurrentWidget(page)

    def _send_to(self, tool_id: str, payload: str) -> None:
        """Tool Input Bridge: open a tool page and prefill its first text field."""
        self._open_tool(tool_id)
        page = self._tool_pages.get(tool_id)
        if page is None:
            return
        if isinstance(page, ToolPage):
            for widget in page._fields.values():
                if isinstance(widget, CommandInput):
                    widget.set_text(payload)
                    return
        if isinstance(page, EncodingToolPage):
            page._input.set_text(payload)

    def _re_run(self, tool_id: str, params: object) -> None:
        """Open a tool page and prefill persisted params for manual re-run."""
        self._open_tool(tool_id)
        page = self._tool_pages.get(tool_id)
        if not isinstance(page, ToolPage) or not isinstance(params, dict):
            return
        for name, value in params.items():
            widget = page._fields.get(name)
            if isinstance(widget, CommandInput) and isinstance(value, str):
                widget.set_text(value)
            elif isinstance(widget, QSpinBox) and isinstance(value, int):
                widget.setValue(value)
            elif isinstance(widget, QComboBox) and value is not None:
                index = widget.findData(value)
                if index >= 0:
                    widget.setCurrentIndex(index)

    def _on_run_requested(self, params: object) -> None:
        self._logger.warning("Tool without an execution backend requested a run: %s", params)

    def _on_task_created(self, task: Task) -> None:
        self._update_task_count()
        self.statusBar().showMessage(f"任务 {task.tool_id} 已创建", 3000)

    def _on_task_updated(self, task: Task) -> None:
        self._update_task_count()

    def _on_task_finished(self, task: Task) -> None:
        self._update_task_count()
        self.statusBar().showMessage(f"任务 {task.tool_id} {task.status.value}", 5000)

    def _update_task_count(self) -> None:
        self._task_count_label.setText(f"任务：{self._context.task_manager.active_count()}")

    def _on_theme_changed(self, theme: str) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            self._theme.apply(app)
        self._logger.info("Theme switched to %s", theme)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._context.config_manager, self._theme, self)
        dialog.exec()

    def closeEvent(self, event: QCloseEvent) -> None:
        try:
            window = WindowSettings(
                width=self.width(),
                height=self.height(),
                x=self.x(),
                y=self.y(),
                maximized=self.isMaximized(),
            )
            self._context.config_manager.update(window=window)
        except Exception:  # pragma: no cover - config save must not block closing
            self._logger.exception("Failed to persist window geometry")
        self._task_bridge.detach()
        event.accept()
