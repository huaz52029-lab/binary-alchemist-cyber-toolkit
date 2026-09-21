"""Plugin failure matrix: one bad plugin must never break the platform."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

from core.plugin_loader import PluginLoader
from core.plugin_manager import PluginManager
from core.plugin_sdk.plugin_definition import PluginStatus
from core.task_manager import TaskManager
from core.tool_registry import ToolRegistry

GOOD_SOURCE = dedent(
    """\
    from core.plugin_sdk import (
        BaseTool, ExecutionContext, PluginContext, ResultStatus,
        ToolCategory, ToolDefinition, ToolParameters, ToolResult,
    )

    class Good(BaseTool):
        definition = ToolDefinition(id="good", name="Good", category=ToolCategory.CTF)
        def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
            return context.make_result(ResultStatus.SUCCESS, "ok")

    def register(context: PluginContext) -> list[BaseTool]:
        return [Good()]
    """
)


def _good_plugin(plugins_dir: Path, name: str, plugin_id: str) -> Path:
    plugin_dir = plugins_dir / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(
            {
                "id": plugin_id,
                "name": name,
                "version": "1.0.0",
                "api_version": "1.0",
            }
        ),
        encoding="utf-8",
    )
    (plugin_dir / "plugin.py").write_text(GOOD_SOURCE, encoding="utf-8")
    return plugin_dir


def test_bad_json_manifest_isolated(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    _good_plugin(plugins_dir, "good", "binaryalchemist.good")
    bad = plugins_dir / "badjson"
    bad.mkdir()
    (bad / "plugin.json").write_text("{not json", encoding="utf-8")
    registry = ToolRegistry()
    manager = PluginManager(registry, plugins_dir, TaskManager(max_workers=2))
    assert manager.load_enabled() == 1
    assert "binaryalchemist.good.good" in registry
    assert manager.get("badjson").status is PluginStatus.FAILED


def test_syntax_error_plugin_isolated(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    _good_plugin(plugins_dir, "good", "binaryalchemist.good")
    bad = plugins_dir / "syntax"
    bad.mkdir()
    (bad / "plugin.json").write_text(
        json.dumps(
            {
                "id": "binaryalchemist.syntax",
                "name": "syntax",
                "version": "1.0.0",
                "api_version": "1.0",
            }
        ),
        encoding="utf-8",
    )
    (bad / "plugin.py").write_text("def register( broken\n", encoding="utf-8")
    registry = ToolRegistry()
    manager = PluginManager(registry, plugins_dir, TaskManager(max_workers=2))
    assert manager.load_enabled() == 1
    assert "binaryalchemist.good.good" in registry
    assert manager.get("binaryalchemist.syntax").status is PluginStatus.FAILED


def test_plugin_id_conflict_does_not_crash(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    _good_plugin(plugins_dir, "first", "binaryalchemist.dup")
    _good_plugin(plugins_dir, "second", "binaryalchemist.dup")
    registry = ToolRegistry()
    manager = PluginManager(registry, plugins_dir, TaskManager(max_workers=2))
    # The registry must contain the namespaced tool exactly once.
    assert manager.load_enabled() == 1
    assert len(registry.list_tools(plugin_id="binaryalchemist.dup")) == 1


def test_duplicate_tool_id_within_plugin_is_reported_not_fatal(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "clash"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(
            {
                "id": "binaryalchemist.clash",
                "name": "clash",
                "version": "1.0.0",
                "api_version": "1.0",
            }
        ),
        encoding="utf-8",
    )
    (plugin_dir / "plugin.py").write_text(
        GOOD_SOURCE + "\ndef register(context):\n    return [Good(), Good()]\n",
        encoding="utf-8",
    )
    registry = ToolRegistry()
    loader = PluginLoader(registry, plugins_dir)
    info = loader.load_plugin(plugin_dir)
    assert info.loaded is True
    assert "binaryalchemist.clash.good" in registry
    assert "已注册" in (info.error or "")
