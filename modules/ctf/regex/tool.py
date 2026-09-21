"""RegexTool: find/findall/groups/replace with templates and safety guards."""

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

MAX_TEXT_LENGTH = 10 * 1024 * 1024
MAX_COMPLEX_TEXT_LENGTH = 4096

REGEX_TEMPLATES: dict[str, str] = {
    "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "ipv6": r"\b(?:[0-9a-fA-F]{0,4}:){2,}[0-9a-fA-F:]*\b",
    "url": r"https?://[^\s'\"<>]+",
    "domain": r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "base64": r"\b[A-Za-z0-9+/]{8,}={0,2}\b",
    "jwt": r"\b[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",
    "hex": r"\b(?:[0-9a-fA-F]{2}\s*){4,}\b",
    "flag": r"(?:flag|ctf|BA)\{[^}\r\n]+\}",
    "windows_path": r"\b[A-Za-z]:\\(?:[^\s'\"<>|*?]+\\)*[^\s'\"<>|*?]+\b",
    "linux_path": r"(?:/[\w.\-]+)+/[\w.\-]+",
    "hash": r"\b[a-fA-F0-9]{32}\b|\b[a-fA-F0-9]{40}\b|\b[a-fA-F0-9]{64}\b",
}

DISPLAY_SPEC: dict[str, Any] = {
    "title": "正则匹配结果",
    "table": {
        "columns": [
            {"field": "index", "label": "序号"},
            {"field": "group", "label": "分组"},
            {"field": "match", "label": "匹配"},
            {"field": "value", "label": "值"},
        ]
    },
}

_COMPLEXITY_PATTERN = re.compile(r"\((?:[^()]*[+*][^()]*)\)[+*]|\+\+|\*\*")


class RegexTool(BaseTool):
    """Regex 分析器：查找/分组/替换，内置常用模板（大文本与高复杂度有保护）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="ctf.regex",
        name="Regex 分析器",
        category=ToolCategory.CTF,
        icon="ctf",
        description="正则查找、分组与替换，内置 IPv4/URL/Flag/JWT 等常用模板。",
        parameters=[
            ToolParameter(
                name="template",
                label="模板",
                kind=ToolParameterKind.CHOICE,
                default="custom",
                choices=["custom", *sorted(REGEX_TEMPLATES)],
                choice_labels=["自定义", *sorted(REGEX_TEMPLATES)],
            ),
            ToolParameter(name="pattern", label="正则表达式", placeholder=r"flag\{[^}]+\}"),
            ToolParameter(
                name="text",
                label="文本",
                kind=ToolParameterKind.MULTILINE,
                placeholder="输入要匹配的文本",
            ),
            ToolParameter(
                name="mode",
                label="操作",
                kind=ToolParameterKind.CHOICE,
                default="findall",
                choices=["findall", "groups", "replace"],
                choice_labels=["查找全部", "分组", "替换"],
            ),
            ToolParameter(
                name="replacement",
                label="替换为",
                placeholder="替换文本",
                visible_when={"mode": "replace"},
            ),
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        text = str(params.get("text", ""))
        if len(text) > MAX_TEXT_LENGTH:
            return context.make_result(ResultStatus.FAILED, "文本超过 10MB 上限，请分段处理。")
        pattern = str(params.get("pattern", "")).strip()
        template = str(params.get("template", "custom"))
        if template != "custom" and not pattern:
            pattern = REGEX_TEMPLATES.get(template, pattern)
        if not pattern:
            return context.make_result(ResultStatus.FAILED, "请输入正则表达式或选择模板。")
        mode = str(params.get("mode", "findall"))
        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            context.error(f"{self.id} 正则无效：{exc}")
            return context.make_result(ResultStatus.FAILED, f"正则表达式无效：{exc}")
        findings: list[Finding] = []
        if _COMPLEXITY_PATTERN.search(pattern):
            if len(text) > MAX_COMPLEX_TEXT_LENGTH:
                return context.make_result(
                    ResultStatus.FAILED,
                    "正则表达式复杂度较高且文本过大，为避免长时间阻塞已拒绝执行；"
                    "请简化表达式或缩短文本。",
                )
            findings.append(
                Finding(
                    title="表达式可能存在较高计算复杂度",
                    severity=Severity.INFO,
                    kind=FindingKind.HEURISTIC,
                    description="检测到嵌套量词等模式，匹配大文本时可能存在灾难性回溯风险。",
                    evidence=f"pattern={pattern[:80]}",
                    source=self.id,
                )
            )
        context.info(f"{self.id} 执行：{mode}，模板 {template}")
        rows: list[dict[str, Any]] = []
        if mode == "replace":
            replacement = str(params.get("replacement", ""))
            replaced = compiled.sub(replacement, text)
            rows.append({"index": 1, "group": "-", "match": "替换结果", "value": replaced})
            summary = "替换完成。"
        else:
            index = 0
            for match in compiled.finditer(text):
                index += 1
                if mode == "groups":
                    for group_index in range(0, compiled.groups + 1):
                        rows.append(
                            {
                                "index": index,
                                "group": group_index,
                                "match": match.group(group_index),
                                "value": match.group(group_index),
                            }
                        )
                else:
                    rows.append(
                        {
                            "index": index,
                            "group": "-",
                            "match": match.group(),
                            "value": match.group(),
                        }
                    )
            summary = f"共 {index} 处匹配。"
        context.info(f"{self.id} 完成：{len(rows)} 行")
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
