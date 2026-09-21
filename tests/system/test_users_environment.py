"""Users and environment tools."""

from __future__ import annotations

import logging
import threading
from types import SimpleNamespace

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.system.environment import EnvironmentTool, redact_environment_value
from modules.system.users import UsersTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-users",
        tool_id="system.users",
        logger=logging.getLogger("tests.users"),
        cancel_event=threading.Event(),
    )


def test_users_tool(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import psutil

    monkeypatch.setattr(
        psutil,
        "users",
        lambda: [
            SimpleNamespace(name="alice", terminal="console", host="PC", started=1726800000.0),
            SimpleNamespace(name="bob", terminal=None, host=None, started=None),
        ],
    )
    result = UsersTool().run({}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert len(result.data) == 2
    assert result.data[0]["name"] == "alice"
    assert result.data[1]["terminal"] == "N/A"


def test_redact_environment_value() -> None:
    assert redact_environment_value("API_KEY", "abc") == ("[REDACTED]", True)
    assert redact_environment_value("MY_PASSWORD", "x") == ("[REDACTED]", True)
    assert redact_environment_value("PATH", "C:\\bin") == ("C:\\bin", False)


def test_environment_tool(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "modules.system.environment.tool.os.environ",
        {"PATH": "C:\\bin", "SECRET_TOKEN": "supersecret", "JAVA_HOME": "C:\\java"},
    )
    result = EnvironmentTool().run({}, _context())
    assert result.status is ResultStatus.SUCCESS
    values = {row["name"]: row["value"] for row in result.data}
    assert values["SECRET_TOKEN"] == "[REDACTED]"
    assert values["PATH"] == "C:\\bin"
    filtered = EnvironmentTool().run({"filter": "java"}, _context())
    assert [row["name"] for row in filtered.data] == ["JAVA_HOME"]
