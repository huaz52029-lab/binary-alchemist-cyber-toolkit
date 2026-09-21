"""Landing page: project identity plus live statistics from the core."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QListWidget,
    QVBoxLayout,
    QWidget,
)

from core import APP_DISPLAY_NAME, APP_VERSION
from core.app_context import AppContext
from ui.icons import IconProvider
from ui.theme import ThemeManager
from ui.widgets.status_card import StatusCard

_DESCRIPTION = "面向信息安全学习、CTF、靶场及授权安全测试的桌面安全工具平台"


class Dashboard(QWidget):
    """Shows project info and counts read live from AppContext services."""

    def __init__(
        self,
        context: AppContext,
        theme_manager: ThemeManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._context = context
        self._theme = theme_manager
        self._icons = IconProvider(context.paths.root / "resources" / "icons")

        title = QLabel(APP_DISPLAY_NAME, self)
        title.setObjectName("dashboardTitle")
        version = QLabel(f"版本 {APP_VERSION}", self)
        version.setObjectName("dashboardVersion")
        subtitle = QLabel(_DESCRIPTION, self)
        subtitle.setObjectName("dashboardSubtitle")
        subtitle.setWordWrap(True)

        self._tools_card = StatusCard(
            title="工具数量",
            value="0",
            description="已注册工具",
            icon=self._icons.icon("dashboard"),
        )
        self._tasks_card = StatusCard(
            title="任务数量",
            value="0",
            description="已提交任务",
            icon=self._icons.icon("history"),
        )
        self._plugins_card = StatusCard(
            title="插件数量",
            value="0",
            description="已发现插件",
            icon=self._icons.icon("plugins"),
        )

        cards_row = QGridLayout()
        cards_row.setSpacing(12)
        cards_row.addWidget(self._tools_card, 0, 0)
        cards_row.addWidget(self._tasks_card, 0, 1)
        cards_row.addWidget(self._plugins_card, 0, 2)

        recent_frame = QFrame(self)
        recent_frame.setObjectName("dashboardRecent")
        recent_layout = QVBoxLayout(recent_frame)
        recent_title = QLabel("最近任务", recent_frame)
        recent_title.setObjectName("sectionTitle")
        self._recent_list = QListWidget(recent_frame)
        self._recent_list.setObjectName("recentTaskList")
        reports_title = QLabel("最近报告", recent_frame)
        reports_title.setObjectName("sectionTitle")
        self._reports_list = QListWidget(recent_frame)
        self._reports_list.setObjectName("recentTaskList")
        recent_layout.addWidget(recent_title)
        recent_layout.addWidget(self._recent_list)
        recent_layout.addWidget(reports_title)
        recent_layout.addWidget(self._reports_list)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addLayout(cards_row)
        layout.addWidget(recent_frame)

    def refresh(self) -> None:
        """Re-read live statistics from the core services."""
        self._tools_card.set_value(len(self._context.tool_registry.list_tools()))
        self._tasks_card.set_value(self._context.task_manager.total_count())
        self._plugins_card.set_value(self._context.plugin_count())
        self._recent_list.clear()
        recent = self._context.history_manager.recent(5)
        if recent:
            for record in recent:
                self._recent_list.addItem(
                    f"[{record['status']}] {record['tool_name']} · {record['task_id'][:8]}"
                )
        else:
            self._recent_list.addItem("暂无任务记录")
        self._reports_list.clear()
        reports, _task_counts = self._context.report_manager.list()
        if reports:
            for report in reports[:5]:
                self._reports_list.addItem(f"{report.title} · {report.updated_at[:16]}")
        else:
            self._reports_list.addItem("暂无报告")
