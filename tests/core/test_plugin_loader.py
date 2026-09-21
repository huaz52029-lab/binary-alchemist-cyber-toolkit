from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

from core.plugin_loader import PluginLoader
from core.tool_registry import ToolRegistry

VALID_TOOL_SOURCE = dedent(
    """\
    from typing import ClassVar

    from core.result import ResultStatus, ToolResult
    from core.task import ExecutionContext
    from core.tool_definition import (
        BaseTool,
        ToolCategory,
        ToolDefinition,
        ToolParameters,
    )

    class DemoTool(BaseTool):
        definition: ClassVar[ToolDefinition] = ToolDefinition(
            id="ctf.demo_plugin",
            name="Demo Plugin Tool",
            category=ToolCategory.CTF,
            description="plugin test tool",
        )

        def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
            return context.make_result(ResultStatus.SUCCESS, "plugin ok")
    """
)


def _write_plugin(
    plugins_dir: Path,
    *,
    name: str = "demo",
    manifest: dict[str, object] | None = None,
    source: str = VALID_TOOL_SOURCE,
) -> Path:
    plugin_dir = plugins_dir / name
    plugin_dir.mkdir(parents=True)
    manifest_data = manifest or {"name": name, "version": "1.0.0", "description": "demo"}
    (plugin_dir / "plugin.json").write_text(json.dumps(manifest_data), encoding="utf-8")
    (plugin_dir / "main.py").write_text(source, encoding="utf-8")
    return plugin_dir


def test_valid_plugin_loads_and_registers(tmp_path: Path) -> None:
    registry = ToolRegistry()
    plugins_dir = tmp_path / "plugins"
    _write_plugin(plugins_dir)
    report = PluginLoader(registry, plugins_dir).load_all()
    assert report.loaded_count == 1
    assert report.failed_count == 0
    assert report.plugins[0].tools == ("ctf.demo_plugin",)
    assert "ctf.demo_plugin" in registry


def test_invalid_manifest_does_not_abort_other_plugins(tmp_path: Path) -> None:
    registry = ToolRegistry()
    plugins_dir = tmp_path / "plugins"
    _write_plugin(plugins_dir, name="bad", manifest={"name": "bad"})
    _write_plugin(plugins_dir, name="good")
    report = PluginLoader(registry, plugins_dir).load_all()
    assert report.loaded_count == 1
    assert report.failed_count == 1
    failed = next(info for info in report.plugins if not info.loaded)
    assert failed.error is not None
    assert "ctf.demo_plugin" in registry


def test_missing_entry_file_is_reported(tmp_path: Path) -> None:
    registry = ToolRegistry()
    plugins_dir = tmp_path / "plugins"
    _write_plugin(plugins_dir, name="noentry")
    (plugins_dir / "noentry" / "main.py").unlink()
    report = PluginLoader(registry, plugins_dir).load_all()
    assert report.failed_count == 1
    assert "找不到插件" in (report.plugins[0].error or "")


def test_plugin_without_tools_loads_but_registers_nothing(tmp_path: Path) -> None:
    registry = ToolRegistry()
    plugins_dir = tmp_path / "plugins"
    _write_plugin(plugins_dir, name="empty", source="# no tools here\n")
    report = PluginLoader(registry, plugins_dir).load_all()
    assert report.loaded_count == 1
    assert report.plugins[0].tools == ()
    assert len(registry) == 0


def test_duplicate_tool_id_is_recorded_as_plugin_error(tmp_path: Path) -> None:
    registry = ToolRegistry()
    plugins_dir = tmp_path / "plugins"
    first = _write_plugin(plugins_dir, name="first")
    loader = PluginLoader(registry, plugins_dir)
    assert loader.load_plugin(first).loaded
    second = _write_plugin(plugins_dir, name="second")
    info = loader.load_plugin(second)
    assert info.loaded
    assert info.tools == ()
    assert "已注册" in (info.error or "")
    assert len(registry) == 1


def test_missing_plugins_dir_yields_empty_report(tmp_path: Path) -> None:
    report = PluginLoader(ToolRegistry(), tmp_path / "nope").load_all()
    assert report.loaded_count == 0
    assert report.failed_count == 0
