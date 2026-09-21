"""BatchAnalysisTool: lightweight static triage over multiple files/directories."""

from __future__ import annotations

from pathlib import Path
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
from infrastructure.filesystem import FileTypeDetector, human_size, iter_chunks
from modules.crypto.hash.hasher import hash_file
from modules.file_analysis.entropy.analyzer import shannon_entropy
from modules.file_analysis.ioc.extractor import extract_iocs
from modules.file_analysis.strings.extractor import extract_strings

DISPLAY_SPEC: dict[str, Any] = {
    "title": "批量文件分析",
    "table": {
        "columns": [
            {"field": "file", "label": "文件"},
            {"field": "type", "label": "类型"},
            {"field": "size", "label": "大小"},
            {"field": "sha256", "label": "SHA256"},
            {"field": "entropy", "label": "熵"},
            {"field": "ioc_count", "label": "IOC"},
            {"field": "status", "label": "状态"},
        ]
    },
}


def _iter_input_files(paths: list[str], recursive: bool, limit: int) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw.strip())
        if path.is_dir():
            if recursive:
                candidates = sorted(p for p in path.rglob("*") if p.is_file())
            else:
                candidates = sorted(p for p in path.iterdir() if p.is_file())
            files.extend(candidates)
        elif path.is_file():
            files.append(path)
        if len(files) >= limit:
            break
    return files[:limit]


class BatchAnalysisTool(BaseTool):
    """批量分析：对多个文件/目录做轻量静态 triage（Hash/类型/熵/IOC）。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="file_analysis.batch",
        name="批量文件分析",
        category=ToolCategory.FILE_ANALYSIS,
        icon="file",
        description="对多个文件或目录批量执行静态分析（不递归默认，限制文件数量，可取消）。",
        parameters=[
            ToolParameter(
                name="paths",
                label="文件或目录（每行一个）",
                kind=ToolParameterKind.MULTILINE,
                placeholder=r"C:\samples\a.exe&#10;C:\samples\dir",
            ),
            ToolParameter(
                name="recursive",
                label="递归子目录",
                kind=ToolParameterKind.CHOICE,
                default="no",
                choices=["no", "yes"],
                choice_labels=["否", "是"],
            ),
            ToolParameter(
                name="max_files",
                label="文件数量上限",
                kind=ToolParameterKind.INTEGER,
                default=100,
                minimum=1,
                maximum=1000,
            ),
        ],
    )

    def __init__(self, detector: FileTypeDetector | None = None) -> None:
        self._detector = detector or FileTypeDetector()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw = str(params.get("paths", "")).strip()
        if not raw:
            return context.make_result(ResultStatus.FAILED, "请提供至少一个文件或目录路径。")
        recursive = str(params.get("recursive", "no")) == "yes"
        limit = int(params.get("max_files", 100))
        raw_lines = raw.splitlines()
        valid_paths: list[str] = []
        error_rows: list[dict[str, Any]] = []
        for line in raw_lines:
            stripped = line.strip()
            candidate = Path(stripped)
            if candidate.is_dir() or candidate.is_file():
                valid_paths.append(stripped)
            else:
                error_rows.append(
                    {
                        "file": stripped or "（空路径）",
                        "type": "-",
                        "size": "-",
                        "sha256": "-",
                        "entropy": "-",
                        "ioc_count": 0,
                        "status": "失败",
                    }
                )
        files = _iter_input_files(valid_paths, recursive, limit)
        if not files:
            if error_rows:
                return context.make_result(
                    ResultStatus.FAILED,
                    "没有找到可分析的文件。",
                    data=error_rows,
                )
            return context.make_result(ResultStatus.FAILED, "没有找到可分析的文件。")
        context.info(f"{self.id} 批量开始：{len(files)} 个文件（递归={recursive}）")
        rows: list[dict[str, Any]] = list(error_rows)
        failed = len(error_rows)
        total = len(files)
        for index, path in enumerate(files, start=1):
            context.raise_if_cancelled()
            row = self._analyze_one(path, is_cancelled=lambda: context.is_cancelled)
            rows.append(row)
            if row["status"] == "失败":
                failed += 1
            context.set_progress(
                index / total * 100.0,
                f"{index}/{total}（成功 {index - failed}，失败 {failed}）",
            )
        findings: list[Finding] = []
        if failed:
            findings.append(
                Finding(
                    title="部分文件分析失败",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description=f"{failed}/{total} 个文件分析失败，其余文件继续完成。",
                    evidence=f"failed={failed}",
                    source=self.id,
                )
            )
        context.info(f"{self.id} 批量完成：成功 {total - failed}，失败 {failed}")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"批量分析完成：{total} 个文件，成功 {total - failed}，失败 {failed}。",
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )

    def _analyze_one(
        self,
        path: Path,
        *,
        is_cancelled: Any = None,
    ) -> dict[str, Any]:
        base = {
            "file": path.name,
            "type": "-",
            "size": "-",
            "sha256": "-",
            "entropy": "-",
            "ioc_count": 0,
            "status": "成功",
        }
        try:
            detected = self._detector.detect(path)
            base["type"] = detected.detected_type
            base["size"] = human_size(path.stat().st_size)
            base["sha256"] = hash_file(path, "SHA256", is_cancelled=is_cancelled)[:16]
            counts = [0] * 256
            total = 0
            for chunk in iter_chunks(path, is_cancelled=is_cancelled):
                for byte in chunk:
                    counts[byte] += 1
                total += len(chunk)
            base["entropy"] = round(shannon_entropy(counts, total), 2)
            records = extract_strings(
                path, encoding="ascii", min_length=4, is_cancelled=is_cancelled
            )
            base["ioc_count"] = len(extract_iocs("\n".join(r.text for r in records)))
        except TaskCancelledError:
            raise
        except Exception:
            base["status"] = "失败"
        return base
