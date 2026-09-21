"""Local filesystem persistence for CTF workspaces and pipelines."""

from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from core.exceptions import FileSystemError
from core.paths import data_root
from modules.ctf.workspace.models import ChallengeMetadata, PipelineDefinition


def workspaces_root() -> Path:
    return data_root() / "ctf" / "workspaces"


def pipelines_root() -> Path:
    return data_root() / "ctf" / "pipelines"


def _slug(name: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]+", "-", name).strip("-").lower()
    return value[:40] or "challenge"


class WorkspaceStore:
    """Creates, lists and persists challenge workspaces and pipelines."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or workspaces_root()

    def create(
        self,
        name: str,
        category: str,
        tags: list[str],
    ) -> ChallengeMetadata:
        workspace_id = f"{_slug(name)}-{uuid.uuid4().hex[:8]}"
        directory = self._root / workspace_id
        try:
            for sub in ("attachments", "notes", "results", "pipelines"):
                (directory / sub).mkdir(parents=True, exist_ok=True)
            metadata = ChallengeMetadata(
                id=workspace_id,
                name=name,
                category=category,
                tags=tags,
            )
            (directory / "metadata.json").write_text(
                metadata.model_dump_json_meta() + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise FileSystemError(str(exc), user_message="无法创建工作区。") from exc
        return metadata

    def list_workspaces(self) -> list[ChallengeMetadata]:
        try:
            if not self._root.is_dir():
                return []
            result: list[ChallengeMetadata] = []
            for directory in sorted(self._root.iterdir()):
                meta_path = directory / "metadata.json"
                if meta_path.is_file():
                    try:
                        result.append(
                            ChallengeMetadata.model_validate(
                                json.loads(meta_path.read_text(encoding="utf-8"))
                            )
                        )
                    except (OSError, ValueError):
                        continue
            return result
        except OSError as exc:
            raise FileSystemError(str(exc), user_message="无法列出工作区。") from exc

    def directory(self, workspace_id: str) -> Path:
        directory = self._root / workspace_id
        if not directory.is_dir():
            raise FileSystemError("workspace not found", user_message="工作区不存在。")
        return directory

    def add_attachment(self, workspace_id: str, file_path: Path) -> Path:
        directory = self.directory(workspace_id)
        target = directory / "attachments" / file_path.name
        try:
            shutil.copy2(file_path, target)
            self._touch(directory)
        except OSError as exc:
            raise FileSystemError(str(exc), user_message="无法添加附件。") from exc
        return target

    def save_result(self, workspace_id: str, result_json: str) -> Path:
        directory = self.directory(workspace_id)
        try:
            parsed = json.loads(result_json)
        except json.JSONDecodeError as exc:
            raise FileSystemError(
                "invalid result json", user_message="结果不是有效的 JSON。"
            ) from exc
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        target = directory / "results" / f"result_{timestamp}_{uuid.uuid4().hex[:4]}.json"
        try:
            target.write_text(
                json.dumps(parsed, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self._touch(directory)
        except OSError as exc:
            raise FileSystemError(str(exc), user_message="无法保存结果。") from exc
        return target

    def save_note(self, workspace_id: str, name: str, content: str) -> Path:
        directory = self.directory(workspace_id)
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", name).strip(".")
        if not safe_name:
            safe_name = "note"
        if not safe_name.endswith(".md"):
            safe_name += ".md"
        target = directory / "notes" / safe_name
        try:
            target.write_text(content, encoding="utf-8")
            self._touch(directory)
        except OSError as exc:
            raise FileSystemError(str(exc), user_message="无法保存笔记。") from exc
        return target

    def save_pipeline(self, name: str, definition: PipelineDefinition) -> Path:
        root = pipelines_root()
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", name).strip(".")
        if not safe_name.endswith(".json"):
            safe_name += ".json"
        target = root / safe_name
        try:
            root.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(definition.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise FileSystemError(str(exc), user_message="无法保存 Pipeline。") from exc
        return target

    def list_pipelines(self) -> list[tuple[str, PipelineDefinition]]:
        root = pipelines_root()
        if not root.is_dir():
            return []
        result: list[tuple[str, PipelineDefinition]] = []
        for path in sorted(root.glob("*.json")):
            try:
                definition = PipelineDefinition.model_validate(
                    json.loads(path.read_text(encoding="utf-8"))
                )
                result.append((path.name, definition))
            except (OSError, ValueError):
                continue
        return result

    @staticmethod
    def _touch(directory: Path) -> None:
        metadata_path = directory / "metadata.json"
        try:
            metadata = ChallengeMetadata.model_validate(
                json.loads(metadata_path.read_text(encoding="utf-8"))
            )
            metadata.updated_at = datetime.now(UTC).isoformat()
            metadata_path.write_text(
                metadata.model_dump_json_meta() + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
