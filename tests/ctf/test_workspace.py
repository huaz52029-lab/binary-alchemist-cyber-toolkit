"""Workspace store and tool round-trips."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.ctf.workspace import WorkspaceStore, WorkspaceTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-ws",
        tool_id="ctf.workspace",
        logger=logging.getLogger("tests.ws"),
        cancel_event=threading.Event(),
    )


def test_create_and_list_roundtrip(tmp_path: Path) -> None:
    store = WorkspaceStore(root=tmp_path / "workspaces")
    metadata = store.create("crypto-01", "crypto", ["rsa", "easy"])
    listed = store.list_workspaces()
    assert len(listed) == 1
    assert listed[0].id == metadata.id
    assert listed[0].tags == ["rsa", "easy"]
    directory = store.directory(metadata.id)
    assert (directory / "metadata.json").is_file()
    assert (directory / "attachments").is_dir()


def test_add_attachment_and_save_result(tmp_path: Path) -> None:
    store = WorkspaceStore(root=tmp_path / "workspaces")
    metadata = store.create("web-01", "web", [])
    attachment = tmp_path / "chall.txt"
    attachment.write_bytes(b"data")
    target = store.add_attachment(metadata.id, attachment)
    assert target.is_file()
    result_path = store.save_result(metadata.id, json.dumps({"status": "SUCCESS"}))
    assert result_path.is_file()
    assert json.loads(result_path.read_text(encoding="utf-8"))["status"] == "SUCCESS"


def test_tool_create_and_list(tmp_path: Path) -> None:
    store = WorkspaceStore(root=tmp_path / "workspaces")
    tool = WorkspaceTool(store=store)
    created = tool.run(
        {"action": "create", "name": "misc-01", "category": "misc", "tags": "a,b"},
        _context(),
    )
    assert created.status is ResultStatus.SUCCESS
    listed = tool.run({"action": "list"}, _context())
    assert listed.status is ResultStatus.SUCCESS
    assert len(listed.data) == 1


def test_notes_roundtrip(tmp_path: Path) -> None:
    from modules.ctf.notes import NotesTool

    store = WorkspaceStore(root=tmp_path / "workspaces")
    metadata = store.create("notes-test", "misc", [])
    notes = NotesTool(store=store)
    saved = notes.run(
        {
            "action": "save",
            "workspace_id": metadata.id,
            "name": "idea",
            "content": "# 思路\nrsa 题目",
        },
        _context(),
    )
    assert saved.status is ResultStatus.SUCCESS
    found = notes.run(
        {"action": "search", "workspace_id": metadata.id, "keyword": "rsa"},
        _context(),
    )
    assert any("rsa" in row["value"] for row in found.data)
