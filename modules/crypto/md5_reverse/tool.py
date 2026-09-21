"""MD5ReverseTool: offline MD5 candidate analysis for CTF/learning."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import ClassVar

from pydantic import ValidationError

from core.exceptions import TaskCancelledError, ToolInputError
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
from infrastructure.crypto import md5_hexdigest
from modules.crypto.md5_reverse.generators import (
    iter_bruteforce_candidates,
    iter_dictionary_candidates,
)
from modules.crypto.md5_reverse.models import (
    MODE_LABELS,
    RESULT_DISPLAY_SPEC,
    VERIFY_DISPLAY_SPEC,
    MD5ReverseInput,
    MD5ReverseResult,
)
from modules.crypto.md5_reverse.validators import (
    LARGE_SPACE_THRESHOLD,
    normalize_charset,
    parse_target_hashes,
    search_space,
    validate_brute_lengths,
)

PROGRESS_INTERVAL = 0.1
SPEED_SAMPLE_INTERVAL = 2048


class MD5ReverseTool(BaseTool):
    """MD5 哈希逆向分析器：离线候选验证 / 字典匹配 / 有限暴力搜索。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="crypto.md5_reverse",
        name="MD5 哈希逆向分析器",
        category=ToolCategory.CRYPTO,
        icon="crypto",
        description=(
            "MD5 是单向哈希，无法直接解密。本工具通过候选明文枚举、本地字典匹配"
            "或有限字符集暴力搜索，寻找与目标 MD5 一致的候选值（完全离线）。"
        ),
        version="1.0.0",
        tags=["md5", "hash", "reverse", "dictionary", "bruteforce"],
        parameters=[
            ToolParameter(
                name="mode",
                label="模式",
                kind=ToolParameterKind.CHOICE,
                default="verify",
                choices=["verify", "dictionary", "bruteforce"],
                choice_labels=["单候选验证", "字典匹配", "暴力尝试"],
            ),
            ToolParameter(
                name="target",
                label="目标 MD5",
                kind=ToolParameterKind.MULTILINE,
                placeholder="5d41402abc4b2a76b9719d911017c592（可多行，批量验证）",
            ),
            ToolParameter(
                name="candidate",
                label="候选明文",
                placeholder="hello（UTF-8 编码计算 MD5）",
                visible_when={"mode": "verify"},
            ),
            ToolParameter(
                name="dictionary_path",
                label="字典文件",
                kind=ToolParameterKind.FILE,
                placeholder="选择本地 UTF-8 文本文件",
                visible_when={"mode": "dictionary"},
            ),
            ToolParameter(
                name="charset",
                label="字符集",
                default="abcdefghijklmnopqrstuvwxyz",
                placeholder="如 abc123",
                visible_when={"mode": "bruteforce"},
            ),
            ToolParameter(
                name="min_length",
                label="最小长度",
                kind=ToolParameterKind.INTEGER,
                default=1,
                minimum=1,
                maximum=8,
                visible_when={"mode": "bruteforce"},
            ),
            ToolParameter(
                name="max_length",
                label="最大长度",
                kind=ToolParameterKind.INTEGER,
                default=5,
                minimum=1,
                maximum=8,
                visible_when={"mode": "bruteforce"},
            ),
        ],
    )

    def run(self, params: ToolParameters, context: ExecutionContext) -> ToolResult:
        try:
            model = MD5ReverseInput.model_validate(dict(params))
        except ValidationError as exc:
            context.error(f"{self.id} 参数校验失败：{exc}")
            return context.make_result(ResultStatus.FAILED, "参数无效，请检查输入。")
        try:
            hashes = parse_target_hashes(model.target)
        except ToolInputError as exc:
            context.error(f"{self.id} Hash 校验失败：{exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        context.info(
            f"{self.id} 启动：模式={MODE_LABELS[model.mode]}，收到 {len(hashes)} 个 32 位 MD5 目标"
        )
        if model.mode == "verify":
            return self._verify(hashes, model, context)
        if len(hashes) != 1:
            message = "字典/暴力模式需要且仅需要一个目标Hash。"
            context.error(f"{self.id} {message}")
            return context.make_result(ResultStatus.FAILED, message)
        target_hash = hashes[0]
        if model.mode == "dictionary":
            return self._dictionary(target_hash, model, context)
        return self._bruteforce(target_hash, model, context)

    def _verify(
        self,
        hashes: list[str],
        model: MD5ReverseInput,
        context: ExecutionContext,
    ) -> ToolResult:
        started = perf_counter()
        digest = md5_hexdigest(model.candidate)
        rows = [
            {
                "hash": value,
                "candidate": model.candidate,
                "matched": "是" if digest == value else "否",
            }
            for value in hashes
        ]
        matched_count = sum(row["matched"] == "是" for row in rows)
        elapsed = perf_counter() - started
        if matched_count:
            summary = f"匹配 {matched_count}/{len(hashes)}：候选与目标 MD5 一致。"
        else:
            summary = "未匹配：候选与目标 MD5 不一致。"
        context.info(f"{self.id} 完成：匹配 {matched_count}/{len(hashes)}，耗时 {elapsed:.4f}s")
        findings: list[Finding] = []
        if matched_count:
            findings.append(
                Finding(
                    title="找到匹配候选",
                    severity=Severity.INFO,
                    kind=FindingKind.FACT,
                    description="在指定候选空间中发现与目标 MD5 一致的候选值。",
                    evidence=f"matched={matched_count}/{len(hashes)}",
                    source=self.id,
                )
            )
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=rows,
            findings=findings,
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": VERIFY_DISPLAY_SPEC,
            },
        )

    def _dictionary(
        self,
        target_hash: str,
        model: MD5ReverseInput,
        context: ExecutionContext,
    ) -> ToolResult:
        raw_path = model.dictionary_path.strip()
        if not raw_path:
            message = "请选择或输入字典文件路径。"
            context.error(f"{self.id} {message}")
            return context.make_result(ResultStatus.FAILED, message)
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            message = "字典文件不存在。"
            context.error(f"{self.id} {message}")
            return context.make_result(ResultStatus.FAILED, message)
        context.info(f"{self.id} 字典模式：文件 {path.name}")
        started = perf_counter()
        attempts = 0
        matched: str | None = None
        last_update = 0.0
        file_size = path.stat().st_size
        read_offset = 0

        def on_read(offset: int) -> None:
            nonlocal read_offset
            read_offset = offset

        try:
            for candidate in iter_dictionary_candidates(path, on_read=on_read):
                if context.is_cancelled:
                    raise TaskCancelledError()
                attempts += 1
                if md5_hexdigest(candidate) == target_hash:
                    matched = candidate
                    break
                now = perf_counter()
                if now - last_update >= PROGRESS_INTERVAL:
                    last_update = now
                    speed = attempts / (now - started)
                    progress = (
                        min(100.0, read_offset / file_size * 100.0) if file_size > 0 else None
                    )
                    context.set_progress(
                        progress,
                        f"已尝试 {attempts}，速度 {speed:.0f} candidates/s",
                    )
        except UnicodeDecodeError:
            context.error(f"{self.id} 字典读取失败：编码无效")
            return context.make_result(
                ResultStatus.FAILED,
                "字典文件不是有效的UTF-8文本，或者文件编码不兼容。",
            )
        except OSError:
            context.error(f"{self.id} 字典读取失败")
            return context.make_result(ResultStatus.FAILED, "无法读取字典文件。")
        elapsed = perf_counter() - started
        speed = attempts / elapsed if elapsed > 0.0 else 0.0
        context.set_progress(100.0, f"完成：已尝试 {attempts}，速度 {speed:.0f} candidates/s")
        return self._finalize_search(
            target_hash,
            "dictionary",
            matched,
            attempts,
            elapsed,
            speed,
            context,
            dictionary_path=str(path),
        )

    def _bruteforce(
        self,
        target_hash: str,
        model: MD5ReverseInput,
        context: ExecutionContext,
    ) -> ToolResult:
        try:
            charset = normalize_charset(model.charset)
            min_length, max_length = validate_brute_lengths(
                model.min_length,
                model.max_length,
            )
        except ToolInputError as exc:
            context.error(f"{self.id} 参数校验失败：{exc.user_message}")
            return context.make_result(ResultStatus.FAILED, exc.user_message)
        space = search_space(charset, min_length, max_length)
        context.info(
            f"{self.id} 暴力模式：字符集 {len(charset)} 个，"
            f"长度 {min_length}-{max_length}，搜索空间 {space}"
        )
        findings: list[Finding] = []
        if space > LARGE_SPACE_THRESHOLD:
            context.warning(f"{self.id} 搜索空间较大（{space} 候选），预计耗时较长")
            findings.append(
                Finding(
                    title="搜索空间较大",
                    severity=Severity.INFO,
                    kind=FindingKind.HEURISTIC,
                    description=(
                        f"当前搜索空间包含 {space} 个候选，预计耗时较长，"
                        "且无法保证在有限时间内完成。"
                    ),
                    recommendation="缩小字符集或降低最大长度。",
                    evidence=f"search_space={space}",
                    source=self.id,
                )
            )
        started = perf_counter()
        attempts = 0
        matched: str | None = None
        last_update = 0.0
        for candidate in iter_bruteforce_candidates(charset, min_length, max_length):
            if context.is_cancelled:
                raise TaskCancelledError()
            attempts += 1
            if md5_hexdigest(candidate) == target_hash:
                matched = candidate
                break
            if attempts % SPEED_SAMPLE_INTERVAL == 0:
                now = perf_counter()
                if now - last_update >= PROGRESS_INTERVAL:
                    last_update = now
                    speed = attempts / (now - started)
                    context.set_progress(
                        min(99.9, attempts / space * 100.0),
                        f"已尝试 {attempts}/{space}，速度 {speed:.0f} candidates/s",
                    )
        elapsed = perf_counter() - started
        speed = attempts / elapsed if elapsed > 0.0 else 0.0
        context.set_progress(100.0, f"完成：已尝试 {attempts}，速度 {speed:.0f} candidates/s")
        return self._finalize_search(
            target_hash,
            "bruteforce",
            matched,
            attempts,
            elapsed,
            speed,
            context,
            charset=charset,
            min_length=min_length,
            max_length=max_length,
            findings=findings,
        )

    def _finalize_search(
        self,
        target_hash: str,
        mode: str,
        matched: str | None,
        attempts: int,
        elapsed: float,
        speed: float,
        context: ExecutionContext,
        *,
        dictionary_path: str | None = None,
        charset: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        findings: list[Finding] | None = None,
    ) -> ToolResult:
        if matched is not None:
            summary = (
                f"{MODE_LABELS.get(mode, mode)}成功：找到候选"
                f"（尝试 {attempts}，{speed:.0f} candidates/s，{elapsed:.2f}s）"
            )
            finding = Finding(
                title="找到匹配候选",
                severity=Severity.INFO,
                kind=FindingKind.FACT,
                description="在指定候选空间中发现与目标 MD5 一致的候选值。",
                evidence=f"mode={mode}, attempts={attempts}",
                source=self.id,
            )
        else:
            summary = (
                "未在当前搜索空间中找到匹配候选。"
                "这并不代表目标 Hash 不存在原文，仅代表当前搜索空间内未找到。"
            )
            finding = Finding(
                title="当前搜索空间内未找到匹配",
                severity=Severity.INFO,
                kind=FindingKind.FACT,
                description=(
                    "在用户指定的候选空间内未找到与目标 MD5 一致的候选值；"
                    "这不代表目标 Hash 不可逆或不存在原文。"
                ),
                evidence=f"mode={mode}, attempts={attempts}",
                source=self.id,
            )
        context.info(
            f"{self.id} 完成：模式={mode}，匹配={matched is not None}，"
            f"尝试 {attempts}，{speed:.0f} candidates/s"
        )
        result = MD5ReverseResult(
            target_hash=target_hash,
            mode=mode,
            matched=matched is not None,
            plaintext=matched,
            attempts=attempts,
            elapsed=round(elapsed, 4),
            speed=round(speed, 1),
            dictionary_path=dictionary_path,
            charset=charset,
            min_length=min_length,
            max_length=max_length,
        )
        return context.make_result(
            ResultStatus.SUCCESS,
            summary,
            data=[result.model_dump(mode="json")],
            findings=[finding, *(findings or [])],
            metadata={
                "tool_id": self.id,
                "tool_version": self.definition.version,
                "display": RESULT_DISPLAY_SPEC,
            },
        )


class MD5ReverseCtfTool(MD5ReverseTool):
    """CTF 快捷入口：复用 MD5 逆向分析器的同一份实现。"""

    definition: ClassVar[ToolDefinition] = ToolDefinition(
        id="ctf.md5_reverse",
        name="MD5 Hash 分析",
        category=ToolCategory.CTF,
        icon="ctf",
        description="MD5 候选验证、本地字典匹配与有限字符集暴力搜索（CTF 快捷入口）。",
        version="1.0.0",
        tags=["md5", "hash", "ctf"],
        parameters=MD5ReverseTool.definition.parameters,
    )
