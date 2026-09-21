"""SQLite repository for task history (paginated, indexed, migrated)."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, cast

from core.history.sanitizer import sanitize_json
from core.persistence import open_database

SCHEMA_VERSION = 1

_MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL UNIQUE,
        tool_id TEXT NOT NULL,
        tool_name TEXT DEFAULT '',
        plugin_id TEXT DEFAULT '',
        category TEXT DEFAULT '',
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT,
        duration REAL,
        summary TEXT DEFAULT '',
        input_summary TEXT DEFAULT '',
        params_json TEXT,
        result_json TEXT,
        artifact_path TEXT,
        result_size INTEGER DEFAULT 0,
        error_message TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_tasks_tool ON tasks(tool_id);
    CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
    CREATE INDEX IF NOT EXISTS idx_tasks_plugin ON tasks(plugin_id);
    """,
]


class HistoryRepository:
    """All SQL for task history; the UI never touches sqlite3 directly."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._lock = threading.RLock()
        self._connection: sqlite3.Connection | None = None
        self._connect()
        self._migrate()

    def _connect(self) -> None:
        self._connection = open_database(self._db_path)
        self._connection.row_factory = sqlite3.Row

    def _migrate(self) -> None:
        assert self._connection is not None
        current = self._connection.execute("PRAGMA user_version").fetchone()[0]
        for version in range(current, len(_MIGRATIONS)):
            with self._connection:
                self._connection.executescript(_MIGRATIONS[version])
                self._connection.execute(f"PRAGMA user_version = {version + 1}")

    @property
    def schema_version(self) -> int:
        assert self._connection is not None
        return int(self._connection.execute("PRAGMA user_version").fetchone()[0])

    def upsert_task(self, record: dict[str, Any]) -> None:
        assert self._connection is not None
        columns = (
            "task_id,tool_id,tool_name,plugin_id,category,status,created_at,started_at,"
            "finished_at,duration,summary,input_summary,params_json,result_json,"
            "artifact_path,result_size,error_message"
        )
        placeholders = ", ".join("?" for _ in columns.split(","))
        values = tuple(record.get(column, "") for column in columns.split(","))
        with self._lock, self._connection:
            self._connection.execute(
                f"""INSERT INTO tasks ({columns}) VALUES ({placeholders})
                    ON CONFLICT(task_id) DO UPDATE SET
                    status=excluded.status,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at,
                    duration=excluded.duration,
                    summary=excluded.summary,
                    result_json=excluded.result_json,
                    artifact_path=excluded.artifact_path,
                    result_size=excluded.result_size,
                    error_message=excluded.error_message""",
                values,
            )

    def query(
        self,
        *,
        search: str = "",
        tool_id: str = "",
        category: str = "",
        status: str = "",
        plugin_id: str = "",
        since: str | None = None,
        order_by: str = "created_at",
        order_desc: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        assert self._connection is not None
        where: list[str] = []
        params: list[Any] = []
        if search:
            where.append(
                "(task_id LIKE ? OR tool_id LIKE ? OR tool_name LIKE ? "
                "OR summary LIKE ? OR plugin_id LIKE ?)"
            )
            params.extend([f"%{search}%"] * 5)
        if tool_id:
            where.append("tool_id = ?")
            params.append(tool_id)
        if category:
            where.append("category = ?")
            params.append(category)
        if status:
            where.append("status = ?")
            params.append(status)
        if plugin_id:
            where.append("plugin_id = ?")
            params.append(plugin_id)
        if since:
            where.append("created_at >= ?")
            params.append(since)
        clause = f" WHERE {' AND '.join(where)}" if where else ""
        direction = "DESC" if order_desc else "ASC"
        allowed_orders = {"created_at", "duration", "tool_id", "status"}
        order_column = order_by if order_by in allowed_orders else "created_at"
        with self._lock:
            count = self._connection.execute(
                f"SELECT COUNT(*) FROM tasks{clause}",
                params,
            ).fetchone()[0]
            rows = self._connection.execute(
                f"""SELECT * FROM tasks{clause}
                    ORDER BY {order_column} {direction}
                    LIMIT ? OFFSET ?""",
                [*params, limit, offset],
            ).fetchall()
        return [self._row_to_dict(row) for row in rows], int(count)

    def get(self, task_id: str) -> dict[str, Any] | None:
        assert self._connection is not None
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def delete(self, task_id: str) -> dict[str, Any] | None:
        assert self._connection is not None
        with self._lock:
            row = self._connection.execute(
                "SELECT artifact_path FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            self._connection.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        return {"artifact_path": row["artifact_path"]} if row else None

    def clear(self) -> list[str]:
        assert self._connection is not None
        with self._lock:
            rows = self._connection.execute("SELECT artifact_path FROM tasks").fetchall()
            self._connection.execute("DELETE FROM tasks")
        return [row["artifact_path"] for row in rows if row["artifact_path"]]

    def interrupted_task_ids(self) -> list[str]:
        assert self._connection is not None
        with self._lock:
            rows = self._connection.execute(
                "SELECT task_id FROM tasks WHERE status IN ('PENDING','RUNNING')"
            ).fetchall()
        return [row["task_id"] for row in rows]

    def mark_interrupted(self, task_ids: list[str]) -> None:
        if not task_ids:
            return
        assert self._connection is not None
        with self._lock, self._connection:
            self._connection.executemany(
                "UPDATE tasks SET status='FAILED', error_message='程序退出导致任务中断。' "
                "WHERE task_id = ?",
                [(task_id,) for task_id in task_ids],
            )

    def referenced_task_ids(self) -> set[str]:
        """Task ids referenced by reports (used to guard deletion)."""
        assert self._connection is not None
        with self._lock:
            try:
                rows = self._connection.execute(
                    "SELECT DISTINCT task_id FROM report_tasks"
                ).fetchall()
            except sqlite3.OperationalError:
                return set()
        return {row["task_id"] for row in rows}

    def distinct(self, column: str) -> list[str]:
        allowed = {"tool_id", "category", "status", "plugin_id"}
        if column not in allowed:
            return []
        assert self._connection is not None
        with self._lock:
            rows = self._connection.execute(
                f"SELECT DISTINCT {column} FROM tasks WHERE {column} != '' ORDER BY {column}"
            ).fetchall()
        return [str(row[column]) for row in rows]

    def artifact_task_ids(self) -> set[str]:
        """Task ids that currently reference an on-disk artifact."""
        assert self._connection is not None
        with self._lock:
            rows = self._connection.execute(
                "SELECT task_id FROM tasks WHERE artifact_path != ''"
            ).fetchall()
        return {str(row["task_id"]) for row in rows}

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        record = dict(row)
        for key in ("params_json", "result_json"):
            if record.get(key):
                try:
                    record[key] = json.loads(record[key])
                except (TypeError, json.JSONDecodeError):
                    record[key] = None
        return cast(dict[str, Any], sanitize_json(record))

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
