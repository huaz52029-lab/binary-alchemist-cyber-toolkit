"""Plugin stress: 10 plugins, 1-5 tools each, enable/disable roundtrips."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

from core.plugin_manager import PluginManager
from core.plugin_sdk.plugin_definition import PluginStatus
from core.task_manager import TaskManager
from core.tool_registry import ToolRegistry


def _plugin_source(count: int) -> str:
    classes = "\n\n".join(
        dedent(
            f"""\
            class Tool{index}(BaseTool):
                definition = ToolDefinition(id="tool{index}", name="tool{index}",
                    category=ToolCategory.CTF)
                def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
                    return context.make_result(ResultStatus.SUCCESS, "ok")"""
        )
        for index in range(count)
    )
    header = dedent(
        """\
        from core.plugin_sdk import (
            BaseTool, ExecutionContext, PluginContext, ResultStatus,
            ToolCategory, ToolDefinition, ToolParameters, ToolResult,
        )

        """
    )
    tools = ", ".join(f"Tool{index}()" for index in range(count))
    register = dedent(
        f"""\

        def register(context: PluginContext) -> list[BaseTool]:
            return [{tools}]
        """
    )
    return header + classes + register


def test_ten_plugins_with_multiple_tools_roundtrip(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    expected: dict[str, int] = {}
    for index in range(10):
        count = index % 5 + 1
        plugin_id = f"binaryalchemist.stress{index}"
        expected[plugin_id] = count
        plugin_dir = plugins_dir / f"stress{index}"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(
            json.dumps(
                {
                    "id": plugin_id,
                    "name": f"stress{index}",
                    "version": "1.0.0",
                    "api_version": "1.0",
                }
            ),
            encoding="utf-8",
        )
        (plugin_dir / "plugin.py").write_text(_plugin_source(count), encoding="utf-8")

    registry = ToolRegistry()
    manager = PluginManager(
        registry,
        plugins_dir,
        TaskManager(max_workers=2),
        state_path=tmp_path / "plugin_state.json",
    )
    assert manager.load_enabled() == 10
    total_tools = sum(expected.values())
    assert len(registry) == total_tools
    for plugin_id, count in expected.items():
        assert len(registry.list_tools(plugin_id=plugin_id)) == count

    # Disabling one plugin removes exactly its tools; others stay untouched.
    manager.disable("binaryalchemist.stress0")
    assert len(registry) == total_tools - expected["binaryalchemist.stress0"]
    assert (
        len(registry.list_tools(plugin_id="binaryalchemist.stress1"))
        == expected["binaryalchemist.stress1"]
    )
    manager.enable("binaryalchemist.stress0")
    assert len(registry) == total_tools
    assert manager.get("binaryalchemist.stress0").status is PluginStatus.ENABLED
