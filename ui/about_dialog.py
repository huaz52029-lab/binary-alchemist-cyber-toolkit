"""About dialog: version, license, third-party notices and safety statement."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core import APP_DISPLAY_NAME, APP_NAME, APP_VERSION
from core.paths import app_root


class AboutDialog(QDialog):
    """Displays program identity, version, license and third-party info."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("aboutDialog")
        self.setWindowTitle("关于")
        self.setMinimumWidth(460)

        title = QLabel(APP_DISPLAY_NAME, self)
        title.setObjectName("pageTitle")
        details = QLabel(
            f"{APP_NAME}\n"
            f"版本：{APP_VERSION}\n"
            "作者：Binary Alchemist\n"
            "面向安全学习、CTF、实验环境与授权测试的桌面安全分析平台。\n"
            "许可证：MIT",
            self,
        )
        details.setWordWrap(True)
        notice = QLabel(
            "主动网络功能仅用于本机、实验室、CTF、靶场及明确授权的测试目标。",
            self,
        )
        notice.setObjectName("aboutNotice")
        notice.setWordWrap(True)

        licenses_button = QPushButton("第三方许可证", self)
        licenses_button.clicked.connect(self._open_licenses)
        close_button = QPushButton("关闭", self)
        close_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(title)
        layout.addWidget(details)
        layout.addSpacing(8)
        layout.addWidget(notice)
        layout.addSpacing(8)
        layout.addWidget(licenses_button)
        layout.addWidget(close_button)

    @staticmethod
    def _open_licenses() -> None:
        path = app_root() / "docs" / "third_party_licenses.md"
        if path.is_file():
            os.startfile(Path(path))
