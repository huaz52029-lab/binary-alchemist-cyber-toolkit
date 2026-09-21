from __future__ import annotations

from pathlib import Path

from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from ui.theme import DARK, LIGHT, ThemeManager


def test_default_theme_is_dark(theme_manager: ThemeManager) -> None:
    assert theme_manager.theme == DARK


def test_switch_emits_once_and_rejects_unknown(
    theme_manager: ThemeManager,
) -> None:
    spy = QSignalSpy(theme_manager.theme_changed)
    assert theme_manager.set_theme(LIGHT)
    assert spy.count() == 1
    assert spy.at(0)[0] == LIGHT
    assert not theme_manager.set_theme("neon")
    assert not theme_manager.set_theme(LIGHT)
    assert spy.count() == 1


def test_load_qss_and_apply(
    theme_manager: ThemeManager,
    qapp: QApplication,
    themes_dir: Path,
) -> None:
    content = theme_manager.load_qss()
    assert "#statusCard" in content
    assert theme_manager.qss_path == themes_dir / "dark.qss"
    theme_manager.apply(qapp)
    assert "#statusCard" in qapp.styleSheet()


def test_palette_colors(theme_manager: ThemeManager) -> None:
    assert theme_manager.log_color("ERROR") == "#d06a6a"
    assert theme_manager.severity_color("CRITICAL") == "#d95454"
    assert theme_manager.log_color("UNKNOWN") == "#9aa7b5"
