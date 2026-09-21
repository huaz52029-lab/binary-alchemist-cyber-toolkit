"""PluginManager lifecycle, enable/disable and persistence."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

from core.plugin_manager import PluginManager
from core.plugin_sdk.plugin_definition import PluginStatus
from core.task_manager import TaskManager
from core.tool_registry import ToolRegistry


def _write_plugin(plugins_dir: Path, name: str, *, enabled: bool = True) -> Path:
    plugin_dir = plugins_dir / name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(
            {
                "id": f"binaryalchemist.{name}",
                "name": name,
                "version": "1.0.0",
                "api_version": "1.0",
                "enabled": enabled,
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
    return plugin_dir


def _manager(tmp_path: Path) -> tuple[PluginManager, ToolRegistry]:
    registry = ToolRegistry()
    task_manager = TaskManager(max_workers=2)
    manager = PluginManager(
        registry,
        tmp_path / "plugins",
        task_manager,
        state_path=tmp_path / "plugin_state.json",
    )
    return manager, registry


def test_scan_and_load_enabled(tmp_path: Path) -> None:
    _write_plugin(tmp_path / "plugins", "alpha")
    _write_plugin(tmp_path / "plugins", "beta", enabled=False)
    manager, registry = _manager(tmp_path)
    assert manager.load_enabled() == 1
    assert "binaryalchemist.alpha.probe" in registry
    assert "binaryalchemist.beta.probe" not in registry
    states = {state.definition.id: state for state in manager.states}
    assert states["binaryalchemist.alpha"].status is PluginStatus.ENABLED
    assert states["binaryalchemist.beta"].status is PluginStatus.DISABLED


def test_enable_disable_roundtrip(tmp_path: Path) -> None:
    _write_plugin(tmp_path / "plugins", "alpha")
    manager, registry = _manager(tmp_path)
    assert manager.disable("binaryalchemist.alpha")
    assert "binaryalchemist.alpha.probe" not in registry
    assert manager.get("binaryalchemist.alpha").status is PluginStatus.DISABLED
    assert manager.enable("binaryalchemist.alpha")
    assert "binaryalchemist.alpha.probe" in registry
    # Persisted state survives a new manager instance.
    registry2 = ToolRegistry()
    manager2 = PluginManager(
        registry2,
        tmp_path / "plugins",
        TaskManager(max_workers=2),
        state_path=tmp_path / "plugin_state.json",
    )
    manager2.load_enabled()
    assert "binaryalchemist.alpha.probe" in registry2


def test_broken_plugin_isolated(tmp_path: Path) -> None:
    _write_plugin(tmp_path / "plugins", "good")
    bad = tmp_path / "plugins" / "bad"
    bad.mkdir()
    (bad / "plugin.json").write_text(
        json.dumps(
            {
                "id": "binaryalchemist.bad",
                "name": "bad",
                "version": "1.0.0",
                "api_version": "1.0",
            }
        ),
        encoding="utf-8",
    )
    (bad / "plugin.py").write_text("raise RuntimeError('boom')\n", encoding="utf-8")
    manager, registry = _manager(tmp_path)
    assert manager.load_enabled() == 1
    assert "binaryalchemist.good.probe" in registry
    assert manager.get("binaryalchemist.bad").status is PluginStatus.FAILED
    assert "boom" in (manager.get("binaryalchemist.bad").error or "")


def test_refresh_reloads(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    _write_plugin(plugins_dir, "alpha")
    manager, registry = _manager(tmp_path)
    manager.load_enabled()
    manager.disable("binaryalchemist.alpha")
    assert "binaryalchemist.alpha.probe" not in registry
    manager.enable("binaryalchemist.alpha")
    assert "binaryalchemist.alpha.probe" in registry


def test_refresh_does_not_duplicate_registration(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    _write_plugin(plugins_dir, "alpha")
    manager, registry = _manager(tmp_path)
    manager.load_enabled()
    manager.refresh()
    manager.refresh()
    plugin_tools = [
        definition.id for definition in registry.list_tools(plugin_id="binaryalchemist.alpha")
    ]
    assert plugin_tools == ["binaryalchemist.alpha.probe"]
