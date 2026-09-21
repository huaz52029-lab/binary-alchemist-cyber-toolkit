"""NotesTool: workspace-scoped Markdown notes (plain text editing)."""

from __future__ import annotations

from typing import Any, ClassVar

from core.exceptions import FileSystemError
from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext
from core.tool_definition import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolParameterKind,
    ToolParameters,
)
from modules.ctf.workspace.store import WorkspaceStore

DISPLAY_SPEC: dict[str, Any] = {
    "title": "CTF Notes",
    "table": {
        "columns": [
            {"field": "section", "label": "分类"},
            {"field": "item", "label": "项目"},
            {"field": "value", "label": "值"},
        ]
    },
}


class NotesTool(BaseTool):
    """CTF Notes：在工作区内保存/列出/搜索 Markdown 笔记（纯文本，本地保存）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="ctf.notes",
        name="CTF Notes",
        category=ToolCategory.CTF,
        icon="ctf",
        description="在工作区保存/列出/搜索 Markdown 笔记，全部本地存储。",
        parameters=[
            ToolParameter(
                name="action",
                label="操作",
                kind=ToolParameterKind.CHOICE,
                default="save",
                choices=["save", "list", "search"],
                choice_labels=["保存笔记", "列出笔记", "搜索笔记"],
            ),
            ToolParameter(name="workspace_id", label="工作区 ID"),
            ToolParameter(
                name="name", label="笔记名称", placeholder="notes", visible_when={"action": "save"}
            ),
            ToolParameter(
                name="content",
                label="笔记内容（Markdown）",
                kind=ToolParameterKind.MULTILINE,
                visible_when={"action": "save"},
            ),
            ToolParameter(name="keyword", label="搜索关键字", visible_when={"action": "search"}),
        ],
    )

    def __init__(self, store: WorkspaceStore | None = None) -> None:
        self._store = store or WorkspaceStore()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        action = str(params.get("action", "save"))
        workspace_id = str(params.get("workspace_id", "")).strip()
        if not workspace_id:
            return context.make_result(ResultStatus.FAILED, "请提供工作区 ID。")
        context.info(f"{self.id} 执行：{action}")
        try:
            directory = self._store.directory(workspace_id)
            if action == "save":
                name = str(params.get("name", "note")).strip()
                target = self._store.save_note(workspace_id, name, str(params.get("content", "")))
                rows = [{"section": "笔记", "item": target.name, "value": str(target)}]
                summary = f"笔记已保存：{target.name}"
            else:
                keyword = str(params.get("keyword", "")).strip().lower()
                notes_dir = directory / "notes"
                rows = []
                for path in sorted(notes_dir.glob("*.md")) if notes_dir.is_dir() else []:
                    if action == "list":
                        rows.append({"section": "笔记", "item": path.name, "value": str(path)})
                    else:
                        content = path.read_text(encoding="utf-8", errors="replace")
                        if keyword in content.lower():
                            for line in content.splitlines():
                                if keyword in line.lower():
                                    rows.append(
                                        {
                                            "section": path.name,
                                            "item": "匹配行",
                                            "value": line[:200],
                                        }
                                    )
                summary = (
                    f"共 {len(rows)} 条结果。" if action == "search" else f"共 {len(rows)} 篇笔记。"
                )
        except FileSystemError as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        context.info(f"{self.id} 完成：{summary}")
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=rows,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
