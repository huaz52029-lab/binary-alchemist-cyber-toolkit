"""UsersTool: read-only user session listing."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext
from core.tool_definition import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameters,
)

DISPLAY_SPEC: dict[str, Any] = {
    "title": "用户与会话",
    "table": {
        "columns": [
            {"field": "name", "label": "用户名"},
            {"field": "terminal", "label": "终端"},
            {"field": "host", "label": "主机"},
            {"field": "started", "label": "登录时间"},
        ]
    },
}


class UsersTool(BaseTool):
    """用户与会话：只读查看当前登录会话（不读取密码或凭据）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="system.users",
        name="用户与会话",
        category=ToolCategory.SYSTEM,
        icon="system",
        description="只读查看当前用户登录会话；不读取任何密码或凭据。",
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        import psutil

        context.info(f"{self.id} 开始读取用户会话")
        rows: list[dict[str, Any]] = []
        for user in psutil.users():
            started = (
                datetime.fromtimestamp(user.started, UTC).isoformat() if user.started else "N/A"
            )
            rows.append(
                {
                    "name": user.name or "N/A",
                    "terminal": user.terminal or "N/A",
                    "host": user.host or "N/A",
                    "started": started,
                }
            )
        context.info(f"{self.id} 完成：{len(rows)} 个会话")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"当前 {len(rows)} 个登录会话。",
            data=rows,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
