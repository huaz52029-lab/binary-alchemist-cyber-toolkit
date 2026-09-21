"""Plugin loader: discovery, validation, namespacing and error isolation."""

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


def _manifest(name: str = "demo") -> dict[str, object]:
    return {
        "id": f"binaryalchemist.{name}",
        "name": name,
        "version": "1.0.0",
        "api_version": "1.0",
    }


def _write_plugin(
    plugins_dir: Path,
    *,
    name: str = "demo",
    manifest: dict[str, object] | None = None,
    source: str = VALID_TOOL_SOURCE,
    entry: str = "plugin.py",
) -> Path:
    plugin_dir = plugins_dir / name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(manifest or _manifest(name)),
        encoding="utf-8",
    )
    (plugin_dir / entry).write_text(source, encoding="utf-8")
    return plugin_dir


def test_valid_plugin_loads_namespaced(tmp_path: Path) -> None:
    registry = ToolRegistry()
    _write_plugin(tmp_path / "plugins")
    report = PluginLoader(registry, tmp_path / "plugins").load_all()
    assert report.loaded_count == 1
    assert report.plugins[0].tools == ("binaryalchemist.demo.ctf.demo_plugin",)
    assert "binaryalchemist.demo.ctf.demo_plugin" in registry
    assert registry.definition_of("binaryalchemist.demo.ctf.demo_plugin").plugin_id == (
        "binaryalchemist.demo"
    )


def test_invalid_manifest_does_not_abort_others(tmp_path: Path) -> None:
    registry = ToolRegistry()
    plugins_dir = tmp_path / "plugins"
    _write_plugin(plugins_dir, name="bad", manifest={"id": "bad"})
    _write_plugin(plugins_dir, name="good")
    report = PluginLoader(registry, plugins_dir).load_all()
    assert report.loaded_count == 1
    assert report.failed_count == 1
    assert "binaryalchemist.good.ctf.demo_plugin" in registry


def test_missing_entry_file_reported(tmp_path: Path) -> None:
    registry = ToolRegistry()
    plugins_dir = tmp_path / "plugins"
    _write_plugin(plugins_dir, name="noentry", entry="nope.py")
    report = PluginLoader(registry, plugins_dir).load_all()
    assert report.failed_count == 1
    assert "入口文件" in (report.plugins[0].error or "")


def test_api_version_incompatible(tmp_path: Path) -> None:
    registry = ToolRegistry()
    plugins_dir = tmp_path / "plugins"
    manifest = _manifest("old")
    manifest["api_version"] = "2.0"
    _write_plugin(plugins_dir, name="old", manifest=manifest)
    report = PluginLoader(registry, plugins_dir).load_all()
    assert report.failed_count == 1
    assert "不兼容" in (report.plugins[0].error or "")


def test_missing_dependency_fails_without_installing(tmp_path: Path) -> None:
    registry = ToolRegistry()
    plugins_dir = tmp_path / "plugins"
    manifest = _manifest("deps")
    manifest["dependencies"] = {"definitely_missing_module_xyz": ">=1.0"}
    _write_plugin(plugins_dir, name="deps", manifest=manifest)
    report = PluginLoader(registry, plugins_dir).load_all()
    assert report.failed_count == 1
    assert "缺少依赖" in (report.plugins[0].error or "")


def test_register_contract(tmp_path: Path) -> None:
    registry = ToolRegistry()
    plugins_dir = tmp_path / "plugins"
    source = dedent(
        """\
        from core.plugin_sdk import (
            BaseTool, ExecutionContext, PluginContext, ResultStatus,
            ToolCategory, ToolDefinition, ToolParameters, ToolResult,
        )

        class RegisteredTool(BaseTool):
            definition = ToolDefinition(
                id="custom", name="Custom", category=ToolCategory.CTF
            )
            def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
                return context.make_result(ResultStatus.SUCCESS, "ok")

        def register(context: PluginContext) -> list[BaseTool]:
            context.save_config({"enabled_option": True})
            return [RegisteredTool()]
        """
    )
    _write_plugin(plugins_dir, name="contract", source=source)
    report = PluginLoader(registry, plugins_dir).load_all()
    assert report.loaded_count == 1
    assert "binaryalchemist.contract.custom" in registry


def test_plugin_without_tools_loads_empty(tmp_path: Path) -> None:
    registry = ToolRegistry()
    plugins_dir = tmp_path / "plugins"
    _write_plugin(plugins_dir, name="empty", source="# no tools\n")
    report = PluginLoader(registry, plugins_dir).load_all()
    assert report.loaded_count == 1
    assert report.plugins[0].tools == ()


def test_unload_removes_only_plugin_tools(tmp_path: Path) -> None:
    registry = ToolRegistry()
    plugins_dir = tmp_path / "plugins"
    _write_plugin(plugins_dir, name="one")
    loader = PluginLoader(registry, plugins_dir)
    loader.load_all()
    assert "binaryalchemist.one.ctf.demo_plugin" in registry
    removed = loader.unload("binaryalchemist.one")
    assert removed == 1
    assert "binaryalchemist.one.ctf.demo_plugin" not in registry
