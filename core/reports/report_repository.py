"""SQLite repository for reports and their task references."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from core.reports.report import Report, ReportTaskRef

_REPORT_MIGRATION = """
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    author TEXT DEFAULT '',
    project TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    template TEXT DEFAULT 'basic',
    sections TEXT DEFAULT '{}',
    conclusion TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    revision INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS report_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    section TEXT DEFAULT 'Findings',
    sort_order INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_report_tasks_report ON report_tasks(report_id);
"""


class ReportRepository:
    """All SQL for reports; UI never touches sqlite3 directly."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._lock = threading.RLock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self._db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        with self._lock, self._connection:
            self._connection.executescript(_REPORT_MIGRATION)

    def save(self, report: Report) -> None:
        payload = {
            "report_id": report.report_id,
            "title": report.title,
            "description": report.description,
            "author": report.author,
            "project": report.project,
            "tags": json.dumps(report.tags, ensure_ascii=False),
            "template": report.template,
            "sections": json.dumps(report.sections, ensure_ascii=False),
            "conclusion": report.conclusion,
            "created_at": report.created_at,
            "updated_at": report.updated_at,
            "revision": report.revision,
        }
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO reports (report_id,title,description,author,project,tags,
                   template,sections,conclusion,created_at,updated_at,revision)
                   VALUES (:report_id,:title,:description,:author,:project,:tags,
                   :template,:sections,:conclusion,:created_at,:updated_at,:revision)
                   ON CONFLICT(report_id) DO UPDATE SET
                   title=excluded.title, description=excluded.description,
                   author=excluded.author, project=excluded.project, tags=excluded.tags,
                   template=excluded.template, sections=excluded.sections,
                   conclusion=excluded.conclusion, updated_at=excluded.updated_at,
                   revision=excluded.revision""",
                payload,
            )
            self._connection.execute(
                "DELETE FROM report_tasks WHERE report_id = ?",
                (report.report_id,),
            )
            for ref in report.task_refs:
                self._connection.execute(
                    "INSERT INTO report_tasks (report_id,task_id,section,sort_order) "
                    "VALUES (?,?,?,?)",
                    (report.report_id, ref.task_id, ref.section, ref.sort_order),
                )

    def get(self, report_id: str) -> Report | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM reports WHERE report_id = ?",
                (report_id,),
            ).fetchone()
            if row is None:
                return None
            refs = self._connection.execute(
                "SELECT * FROM report_tasks WHERE report_id = ? ORDER BY sort_order, id",
                (report_id,),
            ).fetchall()
        return Report(
            report_id=row["report_id"],
            title=row["title"],
            description=row["description"],
            author=row["author"],
            project=row["project"],
            tags=json.loads(row["tags"] or "[]"),
            template=row["template"],
            sections=json.loads(row["sections"] or "{}"),
            conclusion=row["conclusion"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            revision=int(row["revision"]),
            task_refs=[
                ReportTaskRef(
                    task_id=ref["task_id"],
                    section=ref["section"],
                    sort_order=int(ref["sort_order"]),
                )
                for ref in refs
            ],
        )

    def list(self, search: str = "") -> tuple[list[Report], dict[str, int]]:
        clause = ""
        params: list[Any] = []
        if search:
            clause = " WHERE title LIKE ? OR project LIKE ? OR tags LIKE ?"
            params = [f"%{search}%"] * 3
        with self._lock:
            rows = self._connection.execute(
                f"SELECT * FROM reports{clause} ORDER BY updated_at DESC",
                params,
            ).fetchall()
            count_rows = self._connection.execute(
                f"""SELECT r.report_id, COUNT(rt.id) AS task_count
                    FROM reports r LEFT JOIN report_tasks rt ON rt.report_id = r.report_id
                    {clause} GROUP BY r.report_id""",
                params,
            ).fetchall()
        task_counts = {row["report_id"]: int(row["task_count"]) for row in count_rows}
        reports = []
        for row in rows:
            reports.append(
                Report(
                    report_id=row["report_id"],
                    title=row["title"],
                    description=row["description"],
                    author=row["author"],
                    project=row["project"],
                    tags=json.loads(row["tags"] or "[]"),
                    template=row["template"],
                    sections=json.loads(row["sections"] or "{}"),
                    conclusion=row["conclusion"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    revision=int(row["revision"]),
                    task_refs=[],
                )
            )
        return reports, task_counts

    def delete(self, report_id: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "DELETE FROM report_tasks WHERE report_id = ?",
                (report_id,),
            )
            self._connection.execute(
                "DELETE FROM reports WHERE report_id = ?",
                (report_id,),
            )

    def close(self) -> None:
        self._connection.close()
