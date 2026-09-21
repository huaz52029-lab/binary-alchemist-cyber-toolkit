"""TaskHistoryManager: persistence facade between TaskManager and SQLite."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from core.exceptions import FileSystemError
from core.history.history_repository import HistoryRepository
from core.history.sanitizer import sanitize_json, sanitize_text
from core.result import ToolResult
from core.task import Task
from core.tool_registry import ToolRegistry

INLINE_RESULT_LIMIT = 64 * 1024


class TaskHistoryManager:
    """Saves/loads task snapshots; large results spill to artifact files."""

    def __init__(
        self,
        db_path: Path,
        results_dir: Path,
        tool_registry: ToolRegistry | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._repository = HistoryRepository(db_path)
        self._results_dir = Path(results_dir)
        self._results_dir.mkdir(parents=True, exist_ok=True)
        self._tool_registry = tool_registry
        self._logger = logger or logging.getLogger("core.history")
        self._recover_interrupted()

    @property
    def repository(self) -> HistoryRepository:
        return self._repository

    def record_task(self, task: Task) -> None:
        """Persist one task snapshot (called by TaskManager listeners)."""
        definition = (
            self._tool_registry.definition_of(task.tool_id)
            if self._tool_registry is not None
            else None
        )
        duration = None
        if task.started_at is not None and task.finished_at is not None:
            duration = (task.finished_at - task.started_at).total_seconds()
        params_summary = sanitize_text(json.dumps(task.params, ensure_ascii=False, default=str))
        params_json = None
        if definition is not None and definition.input_policy == "safe-to-persist":
            params_json = json.dumps(sanitize_json(task.params), ensure_ascii=False)
        result_json: str | None = None
        artifact_path = ""
        result_size = 0
        if task.result is not None:
            payload = sanitize_json(task.result.model_dump(mode="json"))
            encoded = json.dumps(payload, ensure_ascii=False)
            result_size = len(encoded.encode("utf-8"))
            if result_size <= INLINE_RESULT_LIMIT:
                result_json = encoded
            else:
                artifact_path = str(self._results_dir / f"{task.task_id}.json")
                try:
                    Path(artifact_path).write_text(encoded, encoding="utf-8")
                except OSError as exc:
                    self._logger.warning("Artifact write failed: %s", exc)
                    artifact_path = ""
                    result_json = None
        record = {
            "task_id": task.task_id,
            "tool_id": task.tool_id,
            "tool_name": definition.name if definition else task.tool_id,
            "plugin_id": definition.plugin_id or "" if definition else "",
            "category": definition.category.value if definition else "",
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
            "duration": duration,
            "summary": sanitize_text(task.result.summary if task.result else task.message),
            "input_summary": params_summary[:500],
            "params_json": params_json,
            "result_json": result_json,
            "artifact_path": artifact_path,
            "result_size": result_size,
            "error_message": task.message if task.status.value in ("FAILED", "TIMEOUT") else None,
        }
        self._repository.upsert_task(record)

    def query(
        self,
        **filters: Any,
    ) -> tuple[list[dict[str, Any]], int]:
        return self._repository.query(**filters)

    def get(self, task_id: str) -> dict[str, Any] | None:
        return self._repository.get(task_id)

    def load_result(self, task_id: str) -> ToolResult | None:
        record = self._repository.get(task_id)
        if record is None:
            return None
        try:
            if record.get("result_json"):
                return ToolResult.model_validate(record["result_json"])
            if record.get("artifact_path"):
                payload = json.loads(Path(record["artifact_path"]).read_text(encoding="utf-8"))
                return ToolResult.model_validate(payload)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self._logger.warning("Result load failed for %s: %s", task_id, exc)
        return None

    def delete(self, task_id: str) -> tuple[bool, str]:
        if task_id in self._repository.referenced_task_ids():
            return False, "该任务正在被报告引用，请先从报告中移除。"
        deleted = self._repository.delete(task_id)
        if deleted and deleted.get("artifact_path"):
            self._remove_artifact(deleted["artifact_path"])
        return True, "已删除。"

    def clear(self) -> tuple[int, str]:
        referenced = self._repository.referenced_task_ids()
        if referenced:
            return 0, f"有 {len(referenced)} 条任务被报告引用，无法清空。"
        artifacts = self._repository.clear()
        for artifact in artifacts:
            self._remove_artifact(artifact)
        return len(artifacts), "历史已清空。"

    def recent(self, limit: int = 10) -> list[dict[str, Any]]:
        rows, _total = self._repository.query(limit=limit, offset=0)
        return rows

    def distinct_values(self, column: str) -> list[str]:
        return self._repository.distinct(column)

    def close(self) -> None:
        self._repository.close()

    def _recover_interrupted(self) -> None:
        interrupted = self._repository.interrupted_task_ids()
        if interrupted:
            self._repository.mark_interrupted(interrupted)
            self._logger.warning("Marked %d interrupted tasks as FAILED", len(interrupted))

    def _remove_artifact(self, artifact_path: str) -> None:
        path = Path(artifact_path).resolve()
        if not path.is_relative_to(self._results_dir.resolve()):
            self._logger.warning("Refusing to delete artifact outside results dir: %s", path)
            return
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise FileSystemError(str(exc), user_message="无法删除结果文件。") from exc
