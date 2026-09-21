"""Centralized theme management.

Widget styles live in QSS files under ``resources/themes``. The only colors kept
in Python are the per-line log/severity tints that QSS cannot express for rich
text; they are defined here, per theme, so no widget hard-codes a color.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from core.paths import app_root

DARK = "dark"
LIGHT = "light"
SUPPORTED_THEMES: Final = (DARK, LIGHT)

_DEFAULT_TINT = "#9aa7b5"


@dataclass(frozen=True, slots=True)
class ThemePalette:
    """Theme-dependent tints used by rich-text widgets (logs, findings)."""

    log_colors: Mapping[str, str]
    severity_colors: Mapping[str, str]


_PALETTES: Final[dict[str, ThemePalette]] = {
    DARK: ThemePalette(
        log_colors={
            "DEBUG": "#75849a",
            "INFO": "#a9c3cb",
            "WARNING": "#d9a441",
            "ERROR": "#d06a6a",
            "CRITICAL": "#e05252",
        },
        severity_colors={
            "INFO": "#7f8ea0",
            "LOW": "#5e9fd6",
            "MEDIUM": "#d9a441",
            "HIGH": "#e07a4f",
            "CRITICAL": "#d95454",
        },
    ),
    LIGHT: ThemePalette(
        log_colors={
            "DEBUG": "#6b7686",
            "INFO": "#2f6f78",
            "WARNING": "#8f6310",
            "ERROR": "#b03a3a",
            "CRITICAL": "#b3261e",
        },
        severity_colors={
            "INFO": "#5b6b7b",
            "LOW": "#2d6fa8",
            "MEDIUM": "#8f6310",
            "HIGH": "#c0522f",
            "CRITICAL": "#b3261e",
        },
    ),
}


class ThemeManager(QObject):
    """Loads QSS stylesheets, applies them and exposes per-line color tints."""

    theme_changed = Signal(str)

    def __init__(
        self,
        *,
        theme: str = DARK,
        themes_dir: Path | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._themes_dir = (
            themes_dir if themes_dir is not None else app_root() / "resources" / "themes"
        )
        self._theme = theme if theme in SUPPORTED_THEMES else DARK
        self._logger = logging.getLogger("ui.theme")

    @property
    def theme(self) -> str:
        return self._theme

    @property
    def palette(self) -> ThemePalette:
        return _PALETTES[self._theme]

    @property
    def qss_path(self) -> Path:
        return self._themes_dir / f"{self._theme}.qss"

    def load_qss(self) -> str:
        """Read the current theme stylesheet; returns '' when the file is missing."""
        try:
            return self.qss_path.read_text(encoding="utf-8")
        except OSError:
            self._logger.warning("Theme stylesheet not found: %s", self.qss_path)
            return ""

    def apply(self, app: QApplication) -> None:
        """Apply the current theme stylesheet to the application."""
        app.setStyleSheet(self.load_qss())

    def set_theme(self, theme: str) -> bool:
        """Switch theme; emits :attr:`theme_changed` and returns whether it changed."""
        if theme not in SUPPORTED_THEMES or theme == self._theme:
            return False
        self._theme = theme
        self.theme_changed.emit(theme)
        return True

    def log_color(self, level: str) -> str:
        """Return the tint for a log level name."""
        return self.palette.log_colors.get(level.upper(), _DEFAULT_TINT)

    def severity_color(self, severity: str) -> str:
        """Return the tint for a Finding severity name."""
        return self.palette.severity_colors.get(severity.upper(), _DEFAULT_TINT)
