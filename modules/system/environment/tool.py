"""EnvironmentTool: read-only environment listing with sensitive-value redaction."""

from __future__ import annotations

import os
import re
from typing import Any, ClassVar

from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext
from core.tool_definition import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolParameters,
)

DISPLAY_SPEC: dict[str, Any] = {
    "title": "环境变量",
    "table": {
        "columns": [
            {"field": "name", "label": "变量名"},
            {"field": "value", "label": "值"},
            {"field": "sensitive", "label": "敏感"},
        ]
    },
}

SENSITIVE_PATTERN = re.compile(
    r"(API[_-]?KEY|TOKEN|PASSWORD|PASSWD|SECRET|CREDENTIAL|PRIVATE[_-]?KEY)", re.IGNORECASE
)


def redact_environment_value(name: str, value: str) -> tuple[str, bool]:
    if SENSITIVE_PATTERN.search(name):
        return "[REDACTED]", True
    return value, False


class EnvironmentTool(BaseTool):
    """环境信息：只读查看环境变量，敏感变量值默认脱敏。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="system.environment",
        name="环境信息",
        category=ToolCategory.SYSTEM,
        icon="system",
        description="只读查看环境变量；API_KEY/TOKEN/PASSWORD 等敏感变量值默认脱敏。",
        parameters=[
            ToolParameter(
                name="filter",
                label="搜索关键字",
                placeholder="如 PATH 或 JAVA（留空显示全部）",
            )
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        keyword = str(params.get("filter", "")).strip()
        context.info(f"{self.id} 开始读取环境变量")
        rows: list[dict[str, Any]] = []
        sensitive_count = 0
        for name in sorted(os.environ):
            if keyword and keyword.upper() not in name.upper():
                continue
            value, sensitive = redact_environment_value(name, os.environ[name])
            if sensitive:
                sensitive_count += 1
            rows.append({"name": name, "value": value, "sensitive": "是" if sensitive else "否"})
        context.info(f"{self.id} 完成：{len(rows)} 个变量（{sensitive_count} 个已脱敏）")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"显示 {len(rows)} 个环境变量（{sensitive_count} 个敏感值已脱敏）。",
            data=rows,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
