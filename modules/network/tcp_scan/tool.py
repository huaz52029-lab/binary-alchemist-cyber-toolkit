"""TcpScanTool: bounded, cancellable TCP connect port scan."""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from time import perf_counter
from typing import ClassVar

from pydantic import ValidationError

from core.exceptions import ToolInputError
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
from infrastructure.network import PortProbeResult, ProbeStatus, TcpClient
from modules.network.tcp_scan.models import (
    DISPLAY_SPEC,
    SERVICE_HINTS,
    PortScanInput,
    parse_ports,
)

LARGE_SCAN_THRESHOLD = 2048


class TcpScanTool(BaseTool):
    """TCP 端口扫描：对明确指定的目标执行 TCP Connect 端口检测。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="network.tcp_scan",
        name="TCP 端口扫描",
        category=ToolCategory.NETWORK,
        icon="tcp",
        description="对明确指定的目标执行 TCP Connect 端口扫描（单端口或范围）。",
        version="1.0.0",
        tags=["tcp", "port-scan", "connect"],
        parameters=[
            ToolParameter(name="target", label="目标", placeholder="192.168.1.1 或 example.com"),
            ToolParameter(name="ports", label="端口", placeholder="80 或 80-443"),
            ToolParameter(
                name="timeout",
                label="超时(ms)",
                kind=ToolParameterKind.INTEGER,
                default=2500,
                minimum=100,
                maximum=5000,
            ),
            ToolParameter(
                name="concurrency",
                label="并发数",
                kind=ToolParameterKind.INTEGER,
                default=64,
                minimum=1,
                maximum=256,
            ),
        ],
    )

    def __init__(self, client: TcpClient | None = None) -> None:
        self._client = client or TcpClient(default_timeout=1.0, max_timeout=5.0)

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        try:
            model = PortScanInput.model_validate(dict(params))
        except ValidationError as exc:
            context.error(f"{self.id} 参数校验失败：{exc}")
            return context.make_result(
                ResultStatus.FAILED,
                "扫描参数无效：端口 1-65535，超时 100-5000ms，并发 1-256。",
            )
        try:
            ports = parse_ports(model.ports)
        except ToolInputError as exc:
            context.error(f"{self.id} 参数校验失败：{exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        context.info(
            f"{self.id} 开始扫描 {model.target}，端口 {model.ports}"
            f"（{len(ports)} 个，并发 {model.concurrency}）"
        )
        findings: list[Finding] = []
        if len(ports) > LARGE_SCAN_THRESHOLD:
            context.warning(f"{self.id} 扫描范围较大（{len(ports)} 个端口），请确认目标已获授权")
            findings.append(
                Finding(
                    title="大范围端口扫描",
                    severity=Severity.LOW,
                    kind=FindingKind.RISK,
                    description=(
                        f"扫描端口数量超过 {LARGE_SCAN_THRESHOLD}，可能产生大量连接请求。"
                        "请确认目标已获得明确授权。"
                    ),
                    recommendation="仅在实验环境、靶场或明确授权的目标上执行。",
                    evidence=f"port_count={len(ports)}",
                    source=self.id,
                )
            )
        entries, counts = self._scan(model, ports, context)
        summary = (
            f"扫描完成：共 {len(ports)} 个端口，开放 {counts['open']}，"
            f"关闭 {counts['closed']}，超时 {counts['timeout']}，错误 {counts['error']}"
            f"（{counts['duration']:.1f}s）"
        )
        context.info(f"{self.id} 完成：{summary}")
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=[
                {
                    "port": entry.port,
                    "status": entry.status.value,
                    "latency_ms": round(entry.latency_ms, 2)
                    if entry.latency_ms is not None
                    else None,
                    "service_hint": SERVICE_HINTS.get(entry.port),
                    "error": entry.error,
                }
                for entry in entries
            ],
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )

    def _scan(
        self,
        model: PortScanInput,
        ports: list[int],
        context: ExecutionContext,
    ) -> tuple[list[PortProbeResult], dict[str, int | float]]:
        results: dict[int, PortProbeResult] = {}
        open_count = 0
        closed_count = 0
        timeout_count = 0
        error_count = 0
        started = perf_counter()
        batch_size = max(model.concurrency * 4, 16)
        port_iterator = iter(ports)
        with ThreadPoolExecutor(max_workers=model.concurrency) as executor:
            pending: dict[Future[PortProbeResult], int] = {}

            def submit_batch() -> None:
                for _ in range(batch_size):
                    try:
                        port = next(port_iterator)
                    except StopIteration:
                        break
                    pending[
                        executor.submit(
                            self._client.check_port,
                            model.target,
                            port,
                            model.timeout / 1000.0,
                            is_cancelled=lambda: context.is_cancelled,
                        )
                    ] = port

            submit_batch()
            done_count = 0
            while pending:
                done, _ = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
                if not done:
                    context.raise_if_cancelled()
                    continue
                for future in done:
                    port = pending.pop(future)
                    try:
                        probe = future.result()
                    except Exception as exc:  # defensive: probes normally self-classify
                        probe = PortProbeResult(
                            host=model.target,
                            port=port,
                            family="IPv4",
                            resolved_address="",
                            status=ProbeStatus.ERROR,
                            error=str(exc),
                        )
                    results[port] = probe
                    if probe.status is ProbeStatus.OPEN:
                        open_count += 1
                    elif probe.status is ProbeStatus.CLOSED:
                        closed_count += 1
                    elif probe.status is ProbeStatus.TIMEOUT:
                        timeout_count += 1
                    else:
                        error_count += 1
                    done_count += 1
                    context.set_progress(
                        done_count / len(ports) * 100.0,
                        f"{done_count}/{len(ports)}，开放 {open_count}",
                    )
                context.raise_if_cancelled()
                submit_batch()
        counts: dict[str, int | float] = {
            "open": open_count,
            "closed": closed_count,
            "timeout": timeout_count,
            "error": error_count,
            "duration": perf_counter() - started,
        }
        return [results[port] for port in sorted(results)], counts
