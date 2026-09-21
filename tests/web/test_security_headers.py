"""Security header presence checks and findings."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.network import HttpResponse
from modules.web.security_headers import SecurityHeadersTool, analyze_security_headers


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-sec",
        tool_id="web.security_headers",
        logger=logging.getLogger("tests.sec"),
        cancel_event=threading.Event(),
    )


def _response(headers: dict[str, str]) -> HttpResponse:
    return HttpResponse(
        request_url="https://example.com",
        method="GET",
        final_url="https://example.com",
        status_code=200,
        http_version="HTTP/1.1",
        headers=tuple(headers.items()),
        body=None,
        body_truncated=False,
        elapsed_seconds=0.1,
        redirects=(),
    )


def test_analyzer_statuses() -> None:
    rows = analyze_security_headers(
        _response(
            {
                "Content-Security-Policy": "default-src 'self'",
                "X-Content-Type-Options": "nosniff",
            }
        )
    )
    assert len(rows) == 9
    configured = [row for row in rows if row["status"] == "已配置"]
    assert [row["header"] for row in configured] == [
        "Content-Security-Policy",
        "X-Content-Type-Options",
    ]


def test_tool_counts_and_findings(web_server: str) -> None:
    result = SecurityHeadersTool().run({"url": f"{web_server}/headers"}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert len(result.data) == 9
    assert "已配置 3" in result.summary
    missing = {finding.title for finding in result.findings if finding.title.startswith("缺少")}
    assert "缺少 Strict-Transport-Security" in missing
    assert "缺少 Referrer-Policy" in missing
    missing_findings = [finding for finding in result.findings if finding.title.startswith("缺少")]
    assert all(finding.severity.value == "LOW" for finding in missing_findings)


def test_tool_http_scheme_finding(web_server: str) -> None:
    result = SecurityHeadersTool().run(
        {"url": f"{web_server}/ok"},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    assert any(finding.title == "当前使用 HTTP" for finding in result.findings)
