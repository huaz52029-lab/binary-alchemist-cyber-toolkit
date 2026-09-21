"""Artifact storage helpers: sizes, validation and safe cleanup."""

from __future__ import annotations

from pathlib import Path

from core.exceptions import FileSystemError


class ArtifactManager:
    """Owns the result artifact directory and its safe cleanup operations."""

    def __init__(self, results_dir: Path) -> None:
        self._results_dir = Path(results_dir).resolve()

    @property
    def results_dir(self) -> Path:
        return self._results_dir

    def validate_path(self, path: Path | str) -> Path:
        """Return the resolved path, refusing anything outside results dir."""
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(self._results_dir):
            raise FileSystemError(
                f"artifact path escapes results dir: {resolved}",
                user_message="结果文件路径越界，已拒绝操作。",
            )
        return resolved

    def calculate_size(self) -> int:
        """Total bytes of artifact files (fast stat sum, no content reads)."""
        return sum(path.stat().st_size for path in self.artifact_files() if path.is_file())

    def artifact_files(self) -> list[Path]:
        if not self._results_dir.is_dir():
            return []
        return sorted(path for path in self._results_dir.glob("*.json") if path.is_file())

    def delete_artifact(self, path: Path | str) -> bool:
        resolved = self.validate_path(path)
        if not resolved.is_file():
            return False
        resolved.unlink()
        return True

    def cleanup_orphans(self, referenced_ids: set[str]) -> int:
        """Delete artifact files whose task no longer exists in the database."""
        removed = 0
        for path in self.artifact_files():
            if path.stem not in referenced_ids:
                path.unlink()
                removed += 1
        return removed
