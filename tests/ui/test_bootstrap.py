"""Bootstrap hardening: crash reporting, welcome marker and about dialog."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QWidget

import app as app_module
from core.app_context import AppContext
from ui.about_dialog import AboutDialog
from ui.welcome_dialog import WelcomeDialog


def test_main_reports_fatal_to_crash_log(
    monkeypatch: pytest.MonkeyPatch,
    qapp: QApplication,
    tmp_home: Path,
) -> None:
    def boom(argv: object = None) -> None:
        raise RuntimeError("boom-fatal")

    monkeypatch.setattr(app_module.Application, "from_args", staticmethod(boom))
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    from main import main

    assert main([]) == 1
    crash = tmp_home / "logs" / "crash.log"
    assert crash.is_file()
    assert "boom-fatal" in crash.read_text(encoding="utf-8")
    startup = tmp_home / "logs" / "startup.log"
    assert startup.is_file()
    assert "1.0.0" in startup.read_text(encoding="utf-8")


def test_welcome_dialog_builds_and_shows_once(
    app_context: AppContext,
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_exec(self: WelcomeDialog) -> int:
        calls.append("shown")
        return 0

    monkeypatch.setattr(WelcomeDialog, "exec", fake_exec)
    application = app_module.Application(
        app_context,
        args=argparse.Namespace(self_test=False, smoke_test=False),
    )
    host = QWidget()
    application._show_welcome_once(host)
    application._show_welcome_once(host)
    assert len(calls) == 1
    marker = app_context.paths.data / "welcome.done"
    assert marker.is_file()
    assert marker.read_text(encoding="utf-8") == "1.0.0"


def test_welcome_and_about_dialogs_construct(qapp: QApplication, tmp_path: Path) -> None:
    welcome = WelcomeDialog(tmp_path)
    storage = welcome.findChild(QLabel, "welcomeStorage")
    assert storage is not None
    assert str(tmp_path) in storage.text()
    welcome.deleteLater()

    about = AboutDialog()
    assert about.windowTitle() == "关于"
    texts = [label.text() for label in about.findChildren(QLabel)]
    assert any("1.0.0" in text for text in texts)
    about.deleteLater()
