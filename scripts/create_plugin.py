"""Scaffold a new plugin under plugins/<name>/."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PLUGIN_PY_TEMPLATE = '''"""<Name> plugin entry point."""

from __future__ import annotations

from typing import ClassVar

from core.plugin_sdk import (
    BaseTool,
    ExecutionContext,
    PluginContext,
    ResultStatus,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolParameterKind,
    ToolParameters,
    ToolResult,
)


class <Name>Tool(BaseTool):
    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="<tool_id>",
        name="<Name> Tool",
        category=ToolCategory.CTF,
        description="<description>",
        parameters=[
            ToolParameter(
                name="input",
                label="输入",
                kind=ToolParameterKind.MULTILINE,
                placeholder="输入文本",
            )
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        text = str(params.get("input", ""))
        context.info(f"<tool_id> 处理 {len(text)} 字符")
        return context.make_result(ResultStatus.SUCCESS, f"处理了 {len(text)} 字符。")


def register(context: PluginContext) -> list[BaseTool]:
    context.logger.info("register <name> tools")
    return [<Name>Tool()]
'''


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a new plugin skeleton.")
    parser.add_argument("name", help="plugin name, e.g. my_plugin")
    parser.add_argument("--id", default=None, help="plugin id (default binaryalchemist.<name>)")
    args = parser.parse_args()
    name = _slug(args.name)
    plugin_id = args.id or f"binaryalchemist.{name}"
    target = PROJECT_ROOT / "plugins" / name
    if target.exists():
        print(f"目录已存在：{target}")
        return 1
    (target / "tests").mkdir(parents=True)
    (target / "plugin.json").write_text(
        (
            "{\n"
            f'  "id": "{plugin_id}",\n'
            f'  "name": "{args.name}",\n'
            '  "version": "0.1.0",\n'
            '  "api_version": "1.0",\n'
            '  "author": "you",\n'
            f'  "description": "{args.name} 插件",\n'
            '  "entry_point": "plugin.py",\n'
            '  "enabled": true,\n'
            '  "permissions": [],\n'
            '  "dependencies": {}\n'
            "}\n"
        ),
        encoding="utf-8",
    )
    class_name = "".join(part.capitalize() for part in name.split("_")) or "My"
    (target / "plugin.py").write_text(
        PLUGIN_PY_TEMPLATE.replace("<Name>", class_name)
        .replace("<tool_id>", name)
        .replace("<description>", f"{args.name} 插件工具"),
        encoding="utf-8",
    )
    (target / "README.md").write_text(f"# {args.name}\n\n{args.name} 插件。\n", encoding="utf-8")
    print(f"插件骨架已创建：{target}")
    print(f"插件 ID：{plugin_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
