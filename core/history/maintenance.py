"""Read-only database maintenance: report problems first, clean only on request."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.history.artifacts import ArtifactManager
from core.history.task_history import TaskHistoryManager
from core.reports.report_manager import ReportManager


class DatabaseMaintenance:
    """Detects orphan artifacts and dangling report references.

    Everything here is report-only by default. Deleting anything requires an
    explicit call to the matching ``cleanup_*`` / ``remove_*`` method.
    """

    def __init__(
        self,
        history_manager: TaskHistoryManager,
        report_manager: ReportManager,
        results_dir: Path,
    ) -> None:
        self._history = history_manager
        self._reports = report_manager
        self._artifacts = ArtifactManager(results_dir)

    def orphan_artifact_files(self) -> list[Path]:
        """Artifact files on disk whose task id is absent from the database."""
        referenced = self._history.repository.artifact_task_ids()
        return [path for path in self._artifacts.artifact_files() if path.stem not in referenced]

    def broken_report_refs(self) -> list[dict[str, Any]]:
        """Report task references pointing at tasks that no longer exist."""
        return self._reports.repository.broken_task_refs()

    def calculate_artifact_size(self) -> int:
        return self._artifacts.calculate_size()

    def cleanup_orphan_artifacts(self) -> int:
        """Delete orphan artifacts (validated inside the results directory)."""
        referenced = self._history.repository.artifact_task_ids()
        return self._artifacts.cleanup_orphans(referenced)

    def remove_broken_refs(self) -> int:
        """Delete dangling report references; reports themselves are kept."""
        return self._reports.repository.remove_broken_task_refs()
