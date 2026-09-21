"""HashTool: text/file hash calculation and comparison."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any, ClassVar

from core.exceptions import TaskCancelledError
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
from modules.crypto.hash.hasher import ALGORITHMS, hash_file, hash_text

DISPLAY_SPEC: dict[str, Any] = {
    "title": "Hash 计算结果",
    "sections": [
        {
            "title": "基本信息",
            "items": [
                {"field": "algorithm", "label": "算法"},
                {
                    "field": "input_type",
                    "label": "输入类型",
                    "map": {"text": "文本", "file": "文件"},
                },
                {"field": "input_size", "label": "输入大小(字节)"},
                {"field": "elapsed_ms", "label": "耗时(ms)"},
            ],
        },
        {
            "title": "结果",
            "items": [
                {"field": "hash", "label": "Hash 值"},
                {"field": "compare_hash", "label": "对比目标"},
                {
                    "field": "compare_result",
                    "label": "对比结果",
                    "map": {"MATCH": "一致", "NOT MATCH": "不一致"},
                },
            ],
        },
        {
            "title": "文件",
            "items": [
                {"field": "file_name", "label": "文件名"},
                {"field": "file_size", "label": "文件大小(字节)"},
            ],
        },
    ],
}


class HashTool(BaseTool):
    """Hash 计算器：文本/文件 MD5、SHA1、SHA224、SHA256、SHA384、SHA512。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="crypto.hash",
        name="Hash 计算器",
        category=ToolCategory.CRYPTO,
        icon="crypto",
        description="计算文本或文件的 MD5/SHA1/SHA2 哈希并支持大小写不敏感对比。哈希不是加密。",
        parameters=[
            ToolParameter(
                name="mode",
                label="输入模式",
                kind=ToolParameterKind.CHOICE,
                default="text",
                choices=["text", "file"],
                choice_labels=["文本", "文件"],
            ),
            ToolParameter(
                name="input",
                label="文本",
                kind=ToolParameterKind.MULTILINE,
                placeholder="输入要计算哈希的文本（UTF-8）",
                visible_when={"mode": "text"},
            ),
            ToolParameter(
                name="file_path",
                label="文件",
                kind=ToolParameterKind.FILE,
                placeholder="选择要计算哈希的文件（分块读取）",
                visible_when={"mode": "file"},
            ),
            ToolParameter(
                name="algorithm",
                label="算法",
                kind=ToolParameterKind.CHOICE,
                default="SHA256",
                choices=list(ALGORITHMS),
            ),
            ToolParameter(
                name="compare_hash",
                label="对比 Hash（可选）",
                placeholder="留空不对比；比较忽略大小写",
            ),
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        mode = str(params.get("mode", "text"))
        algorithm = str(params.get("algorithm", "SHA256")).upper()
        if algorithm not in ALGORITHMS:
            return context.make_result(ResultStatus.FAILED, "不支持的哈希算法。")
        compare = str(params.get("compare_hash", "")).strip().lower()
        started = perf_counter()
        data: dict[str, Any] = {"algorithm": algorithm, "input_type": mode}
        try:
            if mode == "file":
                raw_path = str(params.get("file_path", "")).strip()
                if not raw_path:
                    return context.make_result(ResultStatus.FAILED, "请选择要计算哈希的文件。")
                path = Path(raw_path)
                if not path.exists() or not path.is_file():
                    return context.make_result(ResultStatus.FAILED, "文件不存在。")
                context.info(f"{self.id} 文件Hash：{path.name}（{algorithm}）")
                digest = hash_file(
                    path,
                    algorithm,
                    is_cancelled=lambda: context.is_cancelled,
                    on_progress=lambda value: context.set_progress(value),
                )
                data.update(
                    file_name=path.name,
                    file_size=path.stat().st_size,
                    input_size=path.stat().st_size,
                )
            else:
                text = str(params.get("input", ""))
                context.info(f"{self.id} 文本Hash：{len(text.encode('utf-8'))} 字节（{algorithm}）")
                digest = hash_text(text, algorithm)
                data["input_size"] = len(text.encode("utf-8"))
        except TaskCancelledError:
            raise
        except OSError as exc:
            context.error(f"{self.id} 文件读取失败：{exc}")
            return context.make_result(ResultStatus.FAILED, "无法读取文件。")
        elapsed_ms = round((perf_counter() - started) * 1000.0, 2)
        data.update(hash=digest, elapsed_ms=elapsed_ms)
        findings: list[Finding] = []
        summary = f"{algorithm} 计算完成：{digest}"
        if compare:
            match = digest == compare
            data["compare_hash"] = compare
            data["compare_result"] = "MATCH" if match else "NOT MATCH"
            if match:
                summary = f"{algorithm} 与目标一致（MATCH）。"
                findings.append(
                    Finding(
                        title="Hash 一致",
                        severity=Severity.INFO,
                        kind=FindingKind.FACT,
                        description="计算所得哈希与目标哈希一致。",
                        evidence=f"algorithm={algorithm}",
                        source=self.id,
                    )
                )
            else:
                summary = f"{algorithm} 与目标不一致（NOT MATCH）。"
                findings.append(
                    Finding(
                        title="Hash 不一致",
                        severity=Severity.INFO,
                        kind=FindingKind.FACT,
                        description="计算所得哈希与目标哈希不同。这仅表示内容不同，不代表文件不安全或存在风险。",
                        evidence=f"algorithm={algorithm}",
                        source=self.id,
                    )
                )
        context.info(f"{self.id} 完成：{algorithm}，耗时 {elapsed_ms}ms")
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=[data],
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
