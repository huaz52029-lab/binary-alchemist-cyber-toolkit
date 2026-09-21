"""Qt offscreen fixtures shared by the UI tests."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from core.app_context import AppContext
from ui.theme import DARK, ThemeManager

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def qapp() -> Iterator[QApplication]:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.processEvents()


@pytest.fixture
def themes_dir() -> Path:
    return REPO_ROOT / "resources" / "themes"


@pytest.fixture
def theme_manager(qapp: QApplication, themes_dir: Path) -> Iterator[ThemeManager]:
    manager = ThemeManager(theme=DARK, themes_dir=themes_dir)
    yield manager
    manager.set_theme(DARK)


@pytest.fixture
def app_context(tmp_home: Path) -> Iterator[AppContext]:
    context = AppContext.create(load_plugins=False)
    yield context
    context.shutdown()
