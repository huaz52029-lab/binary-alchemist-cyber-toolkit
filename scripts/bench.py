"""Reproducible performance benchmarks for the toolkit.

All numbers come from real runs on this machine; the harness writes nothing
outside the repository's ``work/`` scratch directory and never touches the
network beyond 127.0.0.1.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path

from core.app_context import AppContext
from core.task import ExecutionContext
from core.tool_registry import ToolRegistry
from modules import register_builtin_tools
from modules.crypto.hash.hasher import ALGORITHMS, hash_file_multi
from modules.file_analysis.entropy import FileEntropyTool
from modules.file_analysis.strings import FileStringsTool
from modules.network.tcp_scan import TcpScanTool

MEGABYTE = 1024 * 1024
WORK = Path(__file__).resolve().parents[1] / "work"


def _timed(label: str, fn: Callable[[], object]) -> float:
    started = time.perf_counter()
    fn()
    elapsed = time.perf_counter() - started
    print(f"| {label} | {elapsed:.3f}s |")
    return elapsed


def _context(tool_id: str) -> ExecutionContext:
    return ExecutionContext(
        task_id="bench",
        tool_id=tool_id,
        logger=logging.getLogger("bench"),
        cancel_event=threading.Event(),
    )


def _make_file(path: Path, megabytes: int) -> Path:
    block = ("hello 网安 bench string ABCDEFGH ".encode() * 8192)[: MEGABYTE // 2]
    block += bytes(range(256)) * (MEGABYTE // 512)
    block = block[:MEGABYTE]
    with path.open("wb") as handle:
        for _ in range(megabytes):
            handle.write(block)
    return path


def _startup() -> None:
    started = time.perf_counter()
    context = AppContext.create(load_plugins=False)
    print(f"| AppContext.create | {time.perf_counter() - started:.3f}s |")
    started = time.perf_counter()
    register_builtin_tools(context.tool_registry)
    print(f"| register_builtin_tools(58) | {time.perf_counter() - started:.3f}s |")
    context.shutdown()


def _files() -> None:
    WORK.mkdir(exist_ok=True)
    target = _make_file(WORK / "bench-100mb.bin", 100)
    _timed("hash 100MB (6 algorithms)", lambda: hash_file_multi(target, ALGORITHMS))
    _timed(
        "strings 100MB",
        lambda: FileStringsTool().run(
            {"file_path": str(target), "min_length": 4},
            _context("file.strings"),
        ),
    )
    _timed(
        "entropy 100MB",
        lambda: FileEntropyTool().run(
            {"file_path": str(target)},
            _context("file.entropy"),
        ),
    )


def _network() -> None:
    _timed(
        "TCP scan 500 closed ports",
        lambda: TcpScanTool().run(
            {"target": "127.0.0.1", "ports": "1-500", "timeout": 1000, "concurrency": 32},
            _context("network.tcp_scan"),
        ),
    )


def _registry() -> None:
    from core.result import ResultStatus, ToolResult
    from core.tool_definition import BaseTool, ToolCategory, ToolDefinition, ToolParameters

    class Stub(BaseTool):
        def __init__(self, tool_id: str) -> None:
            self.__dict__["definition"] = ToolDefinition(
                id=tool_id,
                name=tool_id,
                category=ToolCategory.CTF,
            )

        def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
            return context.make_result(ResultStatus.SUCCESS, "ok")

    registry = ToolRegistry()
    _timed(
        "registry 500 register + query",
        lambda: (
            [registry.register(Stub(f"ctf.bench_{i:04d}")) for i in range(500)],
            registry.list_tools(),
            registry.list_tools(category=ToolCategory.CTF),
        ),
    )


def main() -> int:
    print("## Performance benchmark (real runs)")
    print()
    _startup()
    _files()
    _network()
    _registry()
    print()
    print(
        f"*Python {__import__('sys').version.split()[0]}, "
        f"Windows, {time.strftime('%Y-%m-%d %H:%M')}*"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
