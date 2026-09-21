"""PipelineTool: save and execute local tool pipelines."""

from __future__ import annotations

import json
from typing import Any, ClassVar

from core.exceptions import FileSystemError
from core.finding import Finding, FindingKind, Severity
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
from core.tool_registry import ToolRegistry
from modules.ctf.workspace.models import PipelineDefinition
from modules.ctf.workspace.store import WorkspaceStore

DISPLAY_SPEC: dict[str, Any] = {
    "title": "Pipeline 结果",
    "table": {
        "columns": [
            {"field": "step", "label": "步骤"},
            {"field": "tool", "label": "工具"},
            {"field": "output", "label": "输出"},
        ]
    },
}


def _extract_text(result: ToolResult) -> str:
    if result.data and isinstance(result.data[0], dict):
        for key in ("output", "text", "value", "result"):
            if isinstance(result.data[0].get(key), str):
                return str(result.data[0][key])
        return json.dumps(result.data[0], ensure_ascii=False)
    return result.summary


class PipelineTool(BaseTool):
    """CTF Pipeline：保存与执行本地工具链（仅本地工具，不支持主动网络工具）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="ctf.pipeline",
        name="CTF Pipeline",
        category=ToolCategory.CTF,
        icon="ctf",
        description="保存/执行本地工具链（如 Base64→Hex→ROT13），默认不允许主动网络工具。",
        parameters=[
            ToolParameter(
                name="action",
                label="操作",
                kind=ToolParameterKind.CHOICE,
                default="execute",
                choices=["execute", "save", "list"],
                choice_labels=["执行", "保存", "列出"],
            ),
            ToolParameter(
                name="name",
                label="Pipeline 名称",
                placeholder="base64-hex",
                visible_when={"action": "save"},
            ),
            ToolParameter(
                name="pipeline_json",
                label="Pipeline 定义 JSON",
                kind=ToolParameterKind.MULTILINE,
                placeholder='{"name":"demo","pipeline_version":1,"steps":[{"tool":"encoding.base64","params":{"operation":"decode"}}]}',
            ),
            ToolParameter(
                name="input",
                label="初始输入",
                kind=ToolParameterKind.MULTILINE,
                visible_when={"action": "execute"},
            ),
        ],
    )

    def __init__(
        self,
        registry: ToolRegistry,
        store: WorkspaceStore | None = None,
    ) -> None:
        self._registry = registry
        self._store = store or WorkspaceStore()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        action = str(params.get("action", "execute"))
        context.info(f"{self.id} 执行：{action}")
        if action == "save":
            return self._save(params, context)
        if action == "list":
            return self._list(context)
        return self._execute(params, context)

    def _save(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw = str(params.get("pipeline_json", "")).strip()
        name = str(params.get("name", "")).strip()
        if not raw or not name:
            return context.make_result(ResultStatus.FAILED, "请提供 Pipeline 名称与定义 JSON。")
        try:
            definition = PipelineDefinition.model_validate(json.loads(raw))
        except ValueError as exc:
            return context.make_result(ResultStatus.FAILED, f"Pipeline 定义无效：{exc}")
        try:
            target = self._store.save_pipeline(name, definition)
        except FileSystemError as exc:
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        context.info(f"{self.id} 已保存：{target.name}")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"Pipeline 已保存：{target.name}",
            data=[{"step": "-", "tool": target.name, "output": f"{len(definition.steps)} 步"}],
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )

    def _list(self, context: ExecutionContext) -> ToolResult:
        pipelines = self._store.list_pipelines()
        rows = [
            {"step": "-", "tool": name, "output": f"{len(definition.steps)} 步"}
            for name, definition in pipelines
        ]
        context.info(f"{self.id} 列出 {len(pipelines)} 个 Pipeline")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"共 {len(pipelines)} 个已保存 Pipeline。",
            data=rows,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )

    def _execute(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw = str(params.get("pipeline_json", "")).strip()
        if not raw:
            return context.make_result(ResultStatus.FAILED, "请提供 Pipeline 定义 JSON。")
        try:
            definition = PipelineDefinition.model_validate(json.loads(raw))
        except ValueError as exc:
            return context.make_result(ResultStatus.FAILED, f"Pipeline 定义无效：{exc}")
        if definition.pipeline_version != 1:
            return context.make_result(ResultStatus.FAILED, "Pipeline 版本不支持。")
        current = str(params.get("input", ""))
        rows: list[dict[str, Any]] = []
        findings: list[Finding] = []
        for index, step in enumerate(definition.steps, start=1):
            context.raise_if_cancelled()
            if step.tool.startswith(("network.", "web.")):
                return context.make_result(
                    ResultStatus.FAILED,
                    "Pipeline 默认不允许调用主动网络工具。",
                )
            tool = self._registry.get(step.tool)
            if tool is None:
                return context.make_result(
                    ResultStatus.PARTIAL,
                    f"步骤 {index} 工具不存在：{step.tool}",
                    data=rows,
                    findings=[
                        Finding(
                            title="Pipeline 步骤失败",
                            severity=Severity.LOW,
                            kind=FindingKind.FACT,
                            description=f"步骤 {index} 引用的工具 {step.tool} 不存在。",
                            source=self.id,
                        )
                    ],
                )
            step_params = {**step.params, "input": current}
            result = tool.run(step_params, context)
            if not result.is_ok:
                findings.append(
                    Finding(
                        title="Pipeline 步骤失败",
                        severity=Severity.LOW,
                        kind=FindingKind.FACT,
                        description=f"步骤 {index}（{step.tool}）失败：{result.summary}",
                        source=self.id,
                    )
                )
                return context.make_result(
                    ResultStatus.PARTIAL,
                    f"步骤 {index}（{step.tool}）失败。",
                    data=rows,
                    findings=findings,
                )
            output = _extract_text(result)
            rows.append({"step": str(index), "tool": step.tool, "output": output[:500]})
            current = output
        context.info(f"{self.id} 完成：{len(definition.steps)} 步")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"Pipeline「{definition.name}」执行完成（{len(definition.steps)} 步）。",
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
