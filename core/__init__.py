"""Domain core of the Binary Alchemist Cyber Toolkit.

This package owns the application-agnostic models, services and contracts shared by
every layer. Nothing in here may import from ``ui``, ``modules`` or ``infrastructure``.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

APP_NAME = "Binary Alchemist Cyber Toolkit"
APP_DISPLAY_NAME = "二进制炼金术士 · 网安工具箱"

try:
    APP_VERSION = version("binary-alchemist-cyber-toolkit")
except PackageNotFoundError:
    APP_VERSION = "1.0.0"

__all__ = ["APP_DISPLAY_NAME", "APP_NAME", "APP_VERSION"]
