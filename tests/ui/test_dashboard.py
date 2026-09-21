from __future__ import annotations

from core.app_context import AppContext
from core.result import ResultStatus
from ui.dashboard import Dashboard
from ui.theme import ThemeManager


def test_dashboard_reads_live_counts(
    app_context: AppContext,
    theme_manager: ThemeManager,
) -> None:
    dashboard = Dashboard(app_context, theme_manager)
    dashboard.refresh()
    assert dashboard._tools_card.value() == "0"
    assert dashboard._tasks_card.value() == "0"
    assert dashboard._plugins_card.value() == "0"
    assert dashboard._recent_list.count() == 1

    task_id = app_context.task_manager.submit(
        "test.tool",
        {},
        lambda context: context.make_result(ResultStatus.SUCCESS, "ok"),
    )
    app_context.task_manager.wait(task_id, timeout=5.0)
    dashboard.refresh()
    assert dashboard._tasks_card.value() == "1"
    assert dashboard._recent_list.count() == 1
    assert "test.tool" in dashboard._recent_list.item(0).text()
