"""WorkspaceTool: create/list challenges, manage attachments and save results."""

from __future__ import annotations

from pathlib import Path
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
    "title": "CTF 工作台",
    "table": {
        "columns": [
            {"field": "section", "label": "分类"},
            {"field": "item", "label": "项目"},
            {"field": "value", "label": "值"},
        ]
    },
}


class WorkspaceTool(BaseTool):
    """CTF 工作台：本地题目工作区（创建/列出/附件/保存结果），全部本地存储。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="ctf.workspace",
        name="CTF 工作台",
        category=ToolCategory.CTF,
        icon="ctf",
        description="创建/列出本地题目工作区、添加附件与保存结果（附件绝不自动执行）。",
        parameters=[
            ToolParameter(
                name="action",
                label="操作",
                kind=ToolParameterKind.CHOICE,
                default="list",
                choices=["create", "list", "add_attachment", "save_result"],
                choice_labels=["创建工作区", "列出工作区", "添加附件", "保存结果"],
            ),
            ToolParameter(
                name="name",
                label="题目名称",
                placeholder="crypto-01",
                visible_when={"action": "create"},
            ),
            ToolParameter(
                name="category",
                label="分类",
                kind=ToolParameterKind.CHOICE,
                default="crypto",
                choices=["crypto", "web", "reverse", "misc", "forensics", "pwn"],
                visible_when={"action": "create"},
            ),
            ToolParameter(name="tags", label="标签（逗号分隔）", visible_when={"action": "create"}),
            ToolParameter(name="workspace_id", label="工作区 ID"),
            ToolParameter(
                name="file_path",
                label="附件文件",
                kind=ToolParameterKind.FILE,
                visible_when={"action": "add_attachment"},
            ),
            ToolParameter(
                name="result_json",
                label="结果 JSON",
                kind=ToolParameterKind.MULTILINE,
                visible_when={"action": "save_result"},
            ),
        ],
    )

    def __init__(self, store: WorkspaceStore | None = None) -> None:
        self._store = store or WorkspaceStore()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        action = str(params.get("action", "list"))
        context.info(f"{self.id} 执行：{action}")
        try:
            if action == "create":
                name = str(params.get("name", "")).strip()
                if not name:
                    return context.make_result(ResultStatus.FAILED, "请输入题目名称。")
                tags = [
                    tag.strip() for tag in str(params.get("tags", "")).split(",") if tag.strip()
                ]
                metadata = self._store.create(
                    name,
                    str(params.get("category", "crypto")),
                    tags,
                )
                rows = [
                    {"section": "工作区", "item": "ID", "value": metadata.id},
                    {"section": "工作区", "item": "名称", "value": metadata.name},
                    {"section": "工作区", "item": "分类", "value": metadata.category},
                    {"section": "工作区", "item": "标签", "value": ", ".join(metadata.tags)},
                ]
                summary = f"工作区 {metadata.id} 创建完成。"
            elif action == "list":
                workspaces = self._store.list_workspaces()
                rows = [
                    {
                        "section": "工作区",
                        "item": metadata.name,
                        "value": (
                            f"{metadata.id} · {metadata.category} · 更新 {metadata.updated_at[:16]}"
                        ),
                    }
                    for metadata in workspaces
                ]
                summary = f"共 {len(workspaces)} 个工作区。"
            elif action == "add_attachment":
                workspace_id = str(params.get("workspace_id", "")).strip()
                raw_path = str(params.get("file_path", "")).strip()
                if not workspace_id or not raw_path:
                    return context.make_result(ResultStatus.FAILED, "请提供工作区 ID 与附件文件。")
                target = self._store.add_attachment(workspace_id, Path(raw_path))
                rows = [{"section": "附件", "item": target.name, "value": str(target)}]
                summary = f"附件已添加：{target.name}"
            else:
                workspace_id = str(params.get("workspace_id", "")).strip()
                result_json = str(params.get("result_json", "")).strip()
                if not workspace_id or not result_json:
                    return context.make_result(ResultStatus.FAILED, "请提供工作区 ID 与结果 JSON。")
                target = self._store.save_result(workspace_id, result_json)
                rows = [{"section": "结果", "item": target.name, "value": str(target)}]
                summary = f"结果已保存：{target.name}"
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
