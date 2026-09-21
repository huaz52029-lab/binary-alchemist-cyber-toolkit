"""First-run welcome dialog with usage framing and the safety boundary."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from core import APP_DISPLAY_NAME


class WelcomeDialog(QDialog):
    """Shown once on first start; explains scope, storage and boundaries."""

    def __init__(self, data_root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("welcomeDialog")
        self.setWindowTitle(f"欢迎使用 {APP_DISPLAY_NAME}")
        self.setMinimumWidth(560)

        title = QLabel(APP_DISPLAY_NAME, self)
        title.setObjectName("pageTitle")
        intro = QLabel(
            "面向安全学习、CTF、实验环境与授权测试的桌面安全分析工具箱："
            "网络、Web、编码、密码学、文件分析、系统安全、CTF 工作台、"
            "插件、任务历史与报告中心。",
            self,
        )
        intro.setWordWrap(True)
        storage = QLabel(
            f"本地数据位置：{data_root}\n所有分析在本地完成，程序不会上传你的数据、Hash 或样本。",
            self,
        )
        storage.setObjectName("welcomeStorage")
        storage.setWordWrap(True)
        notice = QLabel(
            "安全边界：本工具仅用于信息安全学习、CTF、靶场以及经授权的安全"
            "测试。请只对你拥有或明确获权测试的目标使用主动网络功能。",
            self,
        )
        notice.setObjectName("welcomeNotice")
        notice.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, self)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(title)
        layout.addWidget(intro)
        layout.addSpacing(8)
        layout.addWidget(storage)
        layout.addSpacing(8)
        layout.addWidget(notice)
        layout.addSpacing(8)
        layout.addWidget(buttons)
