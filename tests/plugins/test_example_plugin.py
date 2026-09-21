"""End-to-end test of the bundled example plugin."""

from __future__ import annotations

from pathlib import Path

from core.plugin_manager import PluginManager
from core.result import ResultStatus
from core.task import TaskStatus
from core.task_manager import TaskManager
from core.tool_registry import ToolRegistry

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PLUGIN = REPO_ROOT / "plugins" / "example_plugin"


def _manager(tmp_path: Path) -> tuple[PluginManager, ToolRegistry, TaskManager]:
    registry = ToolRegistry()
    task_manager = TaskManager(max_workers=2)
    manager = PluginManager(
        registry,
        EXAMPLE_PLUGIN.parent,
        task_manager,
        state_path=tmp_path / "plugin_state.json",
    )
    return manager, registry, task_manager


def test_example_plugin_loads_and_runs(tmp_path: Path) -> None:
    manager, registry, task_manager = _manager(tmp_path)
    try:
        assert manager.enable("binaryalchemist.example")
        tool_id = "binaryalchemist.example.text.stats"
        tool = registry.get(tool_id)
        assert tool is not None
        task_id = task_manager.submit_tool(tool, {"input": "hello\nworld"})
        snapshot = task_manager.wait(task_id, timeout=5.0)
        assert snapshot.status is TaskStatus.COMPLETED
        assert snapshot.result is not None
        assert snapshot.result.status is ResultStatus.SUCCESS
        assert snapshot.result.data[0]["characters"] == 11
        assert snapshot.result.data[0]["lines"] == 2
    finally:
        task_manager.shutdown(wait=True)


def test_example_plugin_disable_hides_tool(tmp_path: Path) -> None:
    manager, registry, task_manager = _manager(tmp_path)
    try:
        manager.enable("binaryalchemist.example")
        assert "binaryalchemist.example.text.stats" in registry
        manager.disable("binaryalchemist.example")
        assert "binaryalchemist.example.text.stats" not in registry
    finally:
        task_manager.shutdown(wait=True)


def test_example_plugin_definition() -> None:
    import json

    manifest = json.loads((EXAMPLE_PLUGIN / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["id"] == "binaryalchemist.example"
    assert manifest["api_version"] == "1.0"
    assert manifest["permissions"] == ["filesystem.read"]
