"""ServicesTool: read-only Windows service enumeration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from core.exceptions import DependencyMissingError
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
from infrastructure.system import WindowsServiceProvider

DISPLAY_SPEC: dict[str, Any] = {
    "title": "Windows 服务",
    "table": {
        "columns": [
            {"field": "name", "label": "服务名"},
            {"field": "display_name", "label": "显示名称"},
            {"field": "status", "label": "状态"},
            {"field": "start_type", "label": "启动类型"},
            {"field": "account", "label": "账户"},
            {"field": "description", "label": "描述"},
            {"field": "binary_path", "label": "映像路径"},
        ]
    },
}

START_TYPE_ZH = {
    "AUTO": "自动",
    "DEMAND": "手动",
    "DISABLED": "禁用",
    "BOOT": "引导",
    "SYSTEM": "系统",
    "UNKNOWN": "未知",
}


def _service_findings(rows: list[dict[str, Any]], source: str) -> list[Finding]:
    findings: list[Finding] = []
    for row in rows:
        binary = row.get("binary_path", "")
        if not binary or binary == "N/A":
            continue
        path_part = binary.strip().strip('"').split(" ", 1)[0]
        if path_part and Path(path_part).is_file() is False:
            findings.append(
                Finding(
                    title="服务映像路径不存在",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description=(
                        f"服务「{row['name']}」的映像路径当前无法确认存在，"
                        "需考虑权限、特殊服务与系统状态，不代表服务已失效。"
                    ),
                    evidence=f"service={row['name']}",
                    source=source,
                )
            )
        first_token = binary.strip().split(" ", 1)[0]
        executable_suffixes = (".exe", ".dll", ".sys", ".bat", ".cmd", ".com", ".scr")
        if (
            " " in binary
            and not binary.strip().startswith('"')
            and not first_token.lower().endswith(executable_suffixes)
        ):
            findings.append(
                Finding(
                    title="服务路径包含空格且未使用引号",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description=(
                        f"服务「{row['name']}」的可执行路径包含空格且未使用引号，"
                        "建议结合实际安装方式检查路径解析风险。"
                    ),
                    evidence=f"service={row['name']}",
                    source=source,
                )
            )
    return findings


class ServicesTool(BaseTool):
    """Windows 服务：只读枚举服务状态、启动类型与映像路径（不提供启停/修改）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="system.services",
        name="Windows 服务",
        category=ToolCategory.SYSTEM,
        icon="system",
        description="只读查看 Windows 服务状态与启动类型；本工具不提供启动/停止/修改能力。",
        parameters=[
            ToolParameter(
                name="status_filter",
                label="状态筛选",
                kind=ToolParameterKind.CHOICE,
                default="all",
                choices=["all", "RUNNING", "STOPPED"],
                choice_labels=["全部", "仅 RUNNING", "仅 STOPPED"],
            )
        ],
    )

    def __init__(self, provider: WindowsServiceProvider | None = None) -> None:
        self._provider = provider or WindowsServiceProvider()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        status_filter = str(params.get("status_filter", "all"))
        context.info(f"{self.id} 开始枚举服务")
        try:
            services, errors = self._provider.list_services()
        except DependencyMissingError as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        rows = [
            {
                "name": service.name,
                "display_name": service.display_name,
                "status": service.status,
                "start_type": START_TYPE_ZH.get(service.start_type, service.start_type),
                "account": service.account,
                "description": service.description,
                "binary_path": service.binary_path or "N/A",
            }
            for service in services
            if status_filter == "all" or service.status == status_filter
        ]
        findings = _service_findings(rows, self.id)
        if errors:
            findings.append(
                Finding(
                    title="部分服务信息无法访问",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=f"有 {len(errors)} 个服务信息读取失败，其余服务已正常显示。",
                    evidence=f"errors={len(errors)}",
                    source=self.id,
                )
            )
        context.info(f"{self.id} 完成：{len(services)} 个服务（{len(errors)} 个受限）")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"共 {len(services)} 个服务（显示 {len(rows)} 个）。",
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
