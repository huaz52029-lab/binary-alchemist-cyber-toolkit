"""Plugin management page integration."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

from PySide6.QtWidgets import QApplication

from core.plugin_manager import PluginManager
from core.task_manager import TaskManager
from core.tool_registry import ToolRegistry
from ui.plugin_page import PluginPage


def _write_plugin(plugins_dir: Path) -> None:
    plugin_dir = plugins_dir / "demo"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(
            {
                "id": "binaryalchemist.demo",
                "name": "Demo",
                "version": "1.0.0",
                "api_version": "1.0",
                "enabled": True,
            }
        ),
        encoding="utf-8",
    )
    (plugin_dir / "plugin.py").write_text(
        dedent(
            """\
            from core.plugin_sdk import (
                BaseTool, ExecutionContext, PluginContext, ResultStatus,
                ToolCategory, ToolDefinition, ToolParameters, ToolResult,
            )

            class Tool(BaseTool):
                definition = ToolDefinition(
                    id="probe", name="Probe", category=ToolCategory.CTF
                )
                def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
                    return context.make_result(ResultStatus.SUCCESS, "ok")

            def register(context: PluginContext) -> list[BaseTool]:
                return [Tool()]
            """
        ),
        encoding="utf-8",
    )


def test_plugin_page_list_and_toggle(qapp: QApplication, tmp_path: Path) -> None:
    _write_plugin(tmp_path / "plugins")
    registry = ToolRegistry()
    task_manager = TaskManager(max_workers=2)
    manager = PluginManager(
        registry,
        tmp_path / "plugins",
        task_manager,
        state_path=tmp_path / "plugin_state.json",
    )
    page = PluginPage(manager)
    try:
        assert page._table.rowCount() == 1
        page._table.setCurrentCell(0, 0)
        page._enable_button.click()
        assert "binaryalchemist.demo.probe" in registry
        page._disable_button.click()
        assert "binaryalchemist.demo.probe" not in registry
        page._enable_button.click()
        assert "binaryalchemist.demo.probe" in registry
    finally:
        task_manager.shutdown(wait=True)
