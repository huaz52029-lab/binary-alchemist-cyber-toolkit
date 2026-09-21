"""ModMathTool: modular arithmetic for CTF (big integers supported)."""

from __future__ import annotations

import math
from typing import Any, ClassVar

from core.exceptions import ToolInputError
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

DISPLAY_SPEC: dict[str, Any] = {
    "title": "模运算结果",
    "sections": [
        {
            "title": "结果",
            "items": [
                {"field": "operation", "label": "操作"},
                {"field": "result", "label": "结果"},
            ],
        }
    ],
}


def _parse_int(value: str, field: str) -> int:
    stripped = value.strip()
    try:
        return int(stripped)
    except ValueError as exc:
        raise ToolInputError(
            f"{field} is not an integer",
            user_message=f"{field} 必须是整数。",
        ) from exc


class ModMathTool(BaseTool):
    """模数计算：mod / powmod / gcd / lcm / inverse（支持大整数）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="ctf.mod_math",
        name="模数计算",
        category=ToolCategory.CTF,
        icon="ctf",
        description="计算 a mod n、a^b mod n、gcd、lcm 与模逆元（支持大整数）。",
        input_policy="safe-to-persist",
        parameters=[
            ToolParameter(name="a", label="a", placeholder="如 48"),
            ToolParameter(name="b", label="b", placeholder="如 18"),
            ToolParameter(name="n", label="n（模数）", placeholder="如 1000"),
            ToolParameter(
                name="operation",
                label="操作",
                kind=ToolParameterKind.CHOICE,
                default="mod",
                choices=["mod", "powmod", "gcd", "lcm", "inverse"],
                choice_labels=["a mod n", "a^b mod n", "gcd(a,b)", "lcm(a,b)", "inverse(a,n)"],
            ),
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        operation = str(params.get("operation", "mod"))
        try:
            a = _parse_int(str(params.get("a", "")), "a")
            b = _parse_int(str(params.get("b", "")), "b")
            n = _parse_int(str(params.get("n", "")), "n")
        except ToolInputError as exc:
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        if operation in ("mod", "powmod", "inverse") and n == 0:
            return context.make_result(ResultStatus.FAILED, "模数 n 不能为 0。")
        try:
            if operation == "mod":
                result = a % n
            elif operation == "powmod":
                result = pow(a, b, n)
            elif operation == "gcd":
                result = math.gcd(a, b)
            elif operation == "lcm":
                result = math.lcm(a, b)
            else:
                result = pow(a, -1, n)
        except ValueError as exc:
            context.error(f"{self.id} {exc}")
            return context.make_result(ResultStatus.FAILED, "a 与 n 不互质，模逆元不存在。")
        context.info(f"{self.id} 完成：{operation}")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"{operation}(a={a}, b={b}, n={n}) = {result}",
            data=[{"operation": operation, "result": str(result)}],
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
