"""Security regressions: CSV injection, exporter redaction and path escapes."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from core.exporters import ExportManager
from core.history.task_history import TaskHistoryManager
from core.plugin_loader import PluginLoader
from core.reports.report import TEMPLATE_DIR, load_template
from core.result import ResultStatus, ToolResult
from core.task import Task, TaskStatus
from core.tool_registry import ToolRegistry


def _result() -> ToolResult:
    return ToolResult(
        status=ResultStatus.SUCCESS,
        summary="ok",
        data=[
            {
                "value": "=cmd|' /C calc'!A0",
                "plus": "+2+3",
                "minus": "-1",
                "at": "@SUM(A1:A2)",
                "plain": "hello",
                "headers": {"Authorization": "Bearer secret", "token": "secret"},
            }
        ],
    )


def test_csv_formula_injection_is_neutralized() -> None:
    csv_text = ExportManager.with_defaults().to_string(_result(), "csv")
    assert "'=cmd" in csv_text
    assert "'+2+3" in csv_text
    assert "'@SUM" in csv_text
    assert "hello" in csv_text
    # Plain numeric-looking values must stay readable as numbers.
    assert "-1" in csv_text
    assert "=cmd|" not in csv_text.split("'=cmd", 1)[0]


def test_exporters_redact_sensitive_data_by_default() -> None:
    manager = ExportManager.with_defaults()
    result = _result()
    payload = json.loads(manager.to_string(result, "json"))
    headers = payload["data"][0]["headers"]
    assert headers["Authorization"] == "[REDACTED]"
    assert headers["token"] == "[REDACTED]"
    assert "Bearer secret" not in manager.to_string(result, "json")
    assert "Bearer secret" not in manager.to_string(result, "txt")
    assert "secret" not in manager.to_string(result, "csv")


def test_artifact_deletion_cannot_escape_results_dir(tmp_path: Path) -> None:
    manager = TaskHistoryManager(tmp_path / "toolkit.db", tmp_path / "results")
    outside = tmp_path / "precious.txt"
    outside.write_text("keep me", encoding="utf-8")
    now = datetime.now(UTC)
    task = Task(task_id="t-escape", tool_id="crypto.hash", params={})
    task.status = TaskStatus.COMPLETED
    task.started_at = now
    task.finished_at = now
    task.result = ToolResult(status=ResultStatus.SUCCESS, summary="ok")
    manager.record_task(task)
    # Simulate a tampered artifact path pointing outside the results directory.
    connection = sqlite3.connect(tmp_path / "toolkit.db")
    connection.execute(
        "UPDATE tasks SET artifact_path = ? WHERE task_id = 't-escape'",
        (str(outside),),
    )
    connection.commit()
    connection.close()
    assert manager.delete("t-escape")[0] is True
    assert outside.read_text(encoding="utf-8") == "keep me"
    manager.close()


def test_plugin_entry_cannot_escape_plugin_dir(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugins" / "evil"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(
            {
                "id": "binaryalchemist.evil",
                "name": "evil",
                "version": "1.0.0",
                "api_version": "1.0",
                "entry_point": "../../outside.py",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "outside.py").write_text("raise RuntimeError('never run')\n", encoding="utf-8")
    loader = PluginLoader(ToolRegistry(), tmp_path / "plugins")
    info = loader.load_plugin(plugin_dir)
    assert info.loaded is False
    assert info.error is not None


def test_plugin_manifest_missing_entry_is_rejected(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugins" / "broken"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(
            {
                "id": "binaryalchemist.broken",
                "name": "b",
                "version": "1.0.0",
                "api_version": "1.0",
            }
        ),
        encoding="utf-8",
    )
    loader = PluginLoader(ToolRegistry(), tmp_path / "plugins")
    info = loader.load_plugin(plugin_dir)
    assert info.loaded is False
    assert "入口" in (info.error or "")


def test_report_templates_resolve_from_app_root() -> None:
    # Regression: templates used to depend on the source file layout, which
    # breaks inside a PyInstaller onedir bundle.
    from core.paths import app_root

    assert app_root() / "configs" / "report_templates" == TEMPLATE_DIR
    template = load_template("web_security")
    assert template["name"] == "Web Security Report"
    assert template["sections"]
