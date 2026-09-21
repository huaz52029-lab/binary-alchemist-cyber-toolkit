"""SVG-first icon provider with standard-pixmap fallbacks.

Icons are loaded from ``resources/icons``. When an SVG is missing (e.g. while a
plugin or a future theme ships without assets), a neutral Qt standard icon is
returned instead of an empty icon, keeping the layout stable.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyle

from core.paths import app_root

_FALLBACKS: dict[str, QStyle.StandardPixmap] = {
    "dashboard": QStyle.StandardPixmap.SP_ComputerIcon,
    "network": QStyle.StandardPixmap.SP_DriveNetIcon,
    "system": QStyle.StandardPixmap.SP_ComputerIcon,
    "history": QStyle.StandardPixmap.SP_FileDialogListView,
    "reports": QStyle.StandardPixmap.SP_FileDialogContentsView,
    "settings": QStyle.StandardPixmap.SP_FileDialogDetailedView,
}


class IconProvider:
    """Caches QIcons resolved by name."""

    def __init__(self, icons_dir: Path | None = None) -> None:
        self._icons_dir = icons_dir if icons_dir is not None else app_root() / "resources" / "icons"
        self._cache: dict[str, QIcon] = {}

    def icon(self, name: str) -> QIcon:
        """Return the icon for *name*, falling back to a standard pixmap."""
        cached = self._cache.get(name)
        if cached is not None:
            return cached
        svg_path = self._icons_dir / f"{name}.svg"
        icon = QIcon()
        if svg_path.is_file():
            candidate = QIcon(str(svg_path))
            if not candidate.isNull():
                icon = candidate
        if icon.isNull():
            style = QApplication.style()
            standard = _FALLBACKS.get(name, QStyle.StandardPixmap.SP_FileIcon)
            icon = style.standardIcon(standard) if style is not None else QIcon()
        self._cache[name] = icon
        return icon
