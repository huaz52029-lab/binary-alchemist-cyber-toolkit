"""FileInfoTool: basic metadata plus magic-byte type detection."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from core.exceptions import FileSystemError
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
from infrastructure.filesystem import FileTypeDetector, human_size

DISPLAY_SPEC: dict[str, Any] = {
    "title": "文件信息",
    "sections": [
        {
            "title": "基本信息",
            "items": [
                {"field": "name", "label": "文件名"},
                {"field": "path", "label": "完整路径"},
                {"field": "size", "label": "大小"},
                {"field": "extension", "label": "扩展名"},
            ],
        },
        {
            "title": "时间与属性",
            "items": [
                {"field": "created", "label": "创建时间"},
                {"field": "modified", "label": "修改时间"},
                {"field": "accessed", "label": "访问时间"},
                {"field": "read_only", "label": "只读"},
                {"field": "hidden", "label": "隐藏"},
                {"field": "device_id", "label": "设备 ID"},
            ],
        },
        {
            "title": "类型识别",
            "items": [
                {"field": "detected_type", "label": "检测类型"},
                {"field": "type_description", "label": "类型说明"},
                {"field": "magic_hex", "label": "Magic Bytes"},
                {"field": "extension_type", "label": "扩展名推断类型"},
            ],
        },
    ],
}


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, UTC).isoformat()


class FileInfoTool(BaseTool):
    """文件信息：大小、时间、属性与 Magic Bytes 类型识别。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="file_analysis.file_info",
        name="文件信息",
        category=ToolCategory.FILE_ANALYSIS,
        icon="file",
        description="查看文件大小、时间戳、只读/隐藏属性与 Magic Bytes 检测类型。",
        parameters=[
            ToolParameter(
                name="file_path",
                label="文件",
                kind=ToolParameterKind.FILE,
                placeholder="选择要分析的文件",
            )
        ],
    )

    def __init__(self, detector: FileTypeDetector | None = None) -> None:
        self._detector = detector or FileTypeDetector()

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        raw_path = str(params.get("file_path", "")).strip()
        if not raw_path:
            return context.make_result(ResultStatus.FAILED, "请选择要分析的文件。")
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            return context.make_result(ResultStatus.FAILED, "文件不存在。")
        context.info(f"{self.id} 开始分析：{path.name}")
        try:
            stats = path.stat()
            detected = self._detector.detect(path)
        except FileSystemError as exc:
            context.error(f"{self.id} {exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        attributes = int(getattr(stats, "st_file_attributes", 0))
        extension_type = self._detector.expected_from_extension(path.name)
        row: dict[str, Any] = {
            "name": path.name,
            "path": str(path),
            "size": f"{human_size(stats.st_size)}（{stats.st_size} 字节）",
            "extension": path.suffix or "（无）",
            "created": _iso(stats.st_ctime),
            "modified": _iso(stats.st_mtime),
            "accessed": _iso(stats.st_atime),
            "read_only": "是" if attributes & 0x1 else "否",
            "hidden": "是" if attributes & 0x2 else "否",
            "device_id": str(stats.st_dev),
            "detected_type": detected.detected_type,
            "type_description": detected.description,
            "magic_hex": detected.magic_hex or "（文本）",
            "extension_type": extension_type or "（无映射）",
        }
        findings: list[Finding] = []
        if (
            extension_type
            and detected.detected_type != "Unknown"
            and detected.detected_type != "Text"
            and extension_type != detected.detected_type
        ):
            findings.append(
                Finding(
                    title="文件扩展名与文件实际结构不一致",
                    severity=Severity.LOW,
                    kind=FindingKind.FACT,
                    description=(
                        f"扩展名推断为 {extension_type}，而 Magic Bytes 检测为 "
                        f"{detected.detected_type}。这只是结构不一致，不代表文件恶意。"
                    ),
                    evidence=f"extension={extension_type}, magic={detected.detected_type}",
                    recommendation="结合文件来源与内容进一步确认。",
                    source=self.id,
                )
            )
        context.info(f"{self.id} 完成：类型 {detected.detected_type}")
        return context.make_result(
            ResultStatus.SUCCESS,
            f"{path.name}：{human_size(stats.st_size)}，检测类型 {detected.detected_type}。",
            data=[row],
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": DISPLAY_SPEC,
            },
        )
