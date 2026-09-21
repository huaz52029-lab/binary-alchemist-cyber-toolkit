from __future__ import annotations

from pathlib import Path

from app import Application
from core.app_context import AppContext


def test_context_bootstraps_all_services(tmp_home: Path) -> None:
    context = AppContext.create()
    try:
        assert context.config.theme == "dark"
        assert context.tool_registry.list_tools() == []
        assert context.task_manager.max_workers == 8
        assert set(context.exporter_manager.formats()) == {"json", "csv", "txt"}
    finally:
        context.shutdown()


def test_application_self_test_passes(tmp_home: Path) -> None:
    application = Application.from_args([])
    assert application.run() == 0
