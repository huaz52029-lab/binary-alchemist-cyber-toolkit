"""Resilient SQLite connection bootstrap shared by the repositories.

A corrupt database must never crash application startup: the file is quarantined
next to its original location and a fresh database is created in its place.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def open_database(path: Path, *, logger: logging.Logger | None = None) -> sqlite3.Connection:
    """Open *path* with WAL mode, quarantining a corrupt file instead of crashing."""
    log = logger or logging.getLogger("core.persistence")
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
    except sqlite3.DatabaseError:
        connection.close()
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup = path.with_name(f"{path.name}.corrupt-{timestamp}")
        log.warning("Database %s is corrupt; quarantining as %s", path, backup)
        try:
            path.replace(backup)
        except OSError:
            log.exception("Could not quarantine corrupt database %s", path)
            raise
        connection = sqlite3.connect(path, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
    return connection
