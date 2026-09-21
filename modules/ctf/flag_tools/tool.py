"""FlagToolsTool: candidate flag extraction with quick follow-up analysis."""

from __future__ import annotations

import re
from typing import Any, ClassVar

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
from modules.ctf.auto_decode.decoders import decode_candidates

DEFAULT_PATTERNS = (r"flag\{[^}\r\n]+\}", r"ctf\{[^}\r\n]+\}", r"BA\{[^}\r\n]+\}")

DISPLAY_SPEC: dict[str, Any] = {
    "title": "Flag 候选",
    "table": {
        "columns": [
            {"field": "flag", "label": "候选 Flag"},
            {"field": "pattern", "label": "匹配规则"},
            {"field": "hints", "label": "进一步分析"},
        ]
    },
}


class FlagToolsTool(BaseTool):
    """Flag 提取：按常见/自定义格式提取候选 Flag（不判定正确性）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="ctf.flag_tools",
        name="Flag 提取",
        category=ToolCategory.CTF,
        icon="ctf",
        description="从文本中按常见或自定义格式提取候选 Flag，并给出进一步分析提示。",
        parameters=[
            ToolParameter(
                name="text",
                label="文本",
                kind=ToolParameterKind.MULTILINE,
                placeholder="输入包含 Flag 的文本",
            ),
            ToolParameter(
                name="custom_pattern",
                label="自定义格式（正则）",
                placeholder="留空使用 flag{}/ctf{}/BA{}",
            ),
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        text = str(params.get("text", ""))
        if not text.strip():
            return context.make_result(ResultStatus.FAILED, "请输入要分析的文本。")
        custom = str(params.get("custom_pattern", "")).strip()
        patterns = list(DEFAULT_PATTERNS)
        if custom:
            try:
                re.compile(custom)
            except re.error as exc:
                return context.make_result(ResultStatus.FAILED, f"自定义正则无效：{exc}")
            patterns.append(custom)
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                flag = match.group()
                if flag in seen:
                    continue
                seen.add(flag)
                inner = flag.split("{", 1)[1].rstrip("}")
                hints = decode_candidates(inner, max_depth=1)[:3]
                rows.append(
                    {
                        "flag": flag,
                        "pattern": pattern,
                        "hints": "; ".join(
                            f"{candidate.name}→{candidate.decoded[:60]}" for candidate in hints
                        )
                        or "无明显嵌套编码",
                    }
                )
        context.info(f"{self.id} 完成：{len(rows)} 个候选")
        findings: list[Finding] = []
        if rows:
            findings.append(
                Finding(
                    title="Flag 均为候选",
                    severity=Severity.INFO,
                    kind=FindingKind.HEURISTIC,
                    description="提取结果为候选 Flag，不能确定其正确性；进一步分析仅为启发式提示。",
                    evidence=f"candidate_count={len(rows)}",
                    source=self.id,
                )
            )
        return context.make_result(
            ResultStatus.SUCCESS,
            f"提取到 {len(rows)} 个候选 Flag。" if rows else "未发现 Flag 候选。",
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
