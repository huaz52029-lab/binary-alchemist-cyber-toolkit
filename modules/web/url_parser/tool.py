"""UrlParserTool: structured URL decomposition."""

from __future__ import annotations

from typing import Any, ClassVar
from urllib.parse import parse_qsl, urlsplit

from core.exceptions import ToolInputError
from core.finding import Finding, FindingKind, Severity
from core.result import ResultStatus, ToolResult
from core.task import ExecutionContext
from core.tool_definition import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolParameters,
)
from infrastructure.network import host_scope_note, normalize_web_url

DISPLAY_SPEC: dict[str, Any] = {
    "title": "URL 解析结果",
    "sections": [
        {
            "title": "结构",
            "items": [
                {"field": "scheme", "label": "Scheme"},
                {"field": "hostname", "label": "主机"},
                {"field": "port", "label": "端口"},
                {"field": "username", "label": "用户名"},
                {"field": "password_present", "label": "包含密码字段"},
                {"field": "path", "label": "路径"},
                {"field": "query", "label": "查询串"},
                {"field": "fragment", "label": "片段"},
            ],
        },
        {
            "title": "查询参数",
            "items": [
                {"field": "query_params", "label": "参数"},
            ],
        },
    ],
}


class UrlParserTool(BaseTool):
    """URL 解析器：拆分 scheme/host/port/path/query/fragment 与查询参数。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="web.url_parser",
        name="URL 解析器",
        category=ToolCategory.WEB,
        icon="web",
        description="解析 URL 的结构与查询参数（仅支持 HTTP/HTTPS）。",
        parameters=[
            ToolParameter(
                name="url",
                label="URL",
                placeholder="https://example.com:8443/path?a=1&b=hello#top",
            )
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw = str(params.get("url", "")).strip()
        try:
            url, assumed_https = normalize_web_url(raw)
            split = urlsplit(url)
            port = split.port  # raises ValueError on invalid port
        except ToolInputError as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        except ValueError as exc:
            context.error(f"{self.id} 无效端口：{exc}")
            return context.make_result(ResultStatus.FAILED, "URL 包含无效端口。")
        if not split.hostname:
            return context.make_result(ResultStatus.FAILED, "URL 缺少主机名。")
        query_items = parse_qsl(split.query, keep_blank_values=True)
        query_params = "; ".join(f"{key}={value}" for key, value in query_items)
        row: dict[str, Any] = {
            "scheme": split.scheme,
            "hostname": split.hostname,
            "port": port,
            "username": split.username,
            "password_present": split.password is not None,
            "path": split.path or "/",
            "query": split.query,
            "fragment": split.fragment,
            "query_params": query_params or None,
        }
        findings: list[Finding] = []
        if assumed_https:
            findings.append(
                Finding(
                    title="已按 HTTPS 解释",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description="输入未包含协议，已自动按 https:// 解释。",
                    source=self.id,
                )
            )
        if split.scheme == "http":
            findings.append(
                Finding(
                    title="URL 使用明文 HTTP",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description="该 URL 使用未加密的 HTTP 协议传输。",
                    source=self.id,
                )
            )
        if split.username is not None:
            findings.append(
                Finding(
                    title="URL 包含用户信息字段",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description="URL 中包含 username 字段。",
                    source=self.id,
                )
            )
        if split.password is not None:
            findings.append(
                Finding(
                    title="URL 包含密码字段",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description=(
                        "URL 中包含 password 字段，属于敏感信息，请避免在日志或分享中暴露。"
                    ),
                    source=self.id,
                )
            )
        note = host_scope_note(split.hostname)
        if note:
            findings.append(
                Finding(
                    title="本机/私有网络目标",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=note,
                    source=self.id,
                )
            )
        context.info(f"{self.id} 解析完成：{split.scheme}://{split.hostname}")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"URL 解析完成：{split.scheme}://{split.hostname}（路径 {split.path or '/'}）",
            data=[row],
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
