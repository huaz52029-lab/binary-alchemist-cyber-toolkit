"""Thin entry point; all real work lives in :mod:`app`.

The bootstrap is wrapped in a top-level exception handler so a failure never
shows a raw traceback to the user: the details go to ``logs/crash.log`` and a
short message is shown instead.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from app import Application
from core import APP_VERSION
from core.crash import write_crash_report
from core.paths import data_root


def _logs_dir() -> Path:
    directory = data_root() / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _report_fatal() -> None:
    crash_log = write_crash_report(*sys.exc_info())
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        QApplication.instance() or QApplication(sys.argv)
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Binary Alchemist Cyber Toolkit")
        box.setText("程序遇到未处理错误。")
        box.setInformativeText(f"详细信息已写入：\n{crash_log}")
        view_button = box.addButton("查看日志", QMessageBox.ButtonRole.ActionRole)
        box.addButton("关闭程序", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is view_button:
            os.startfile(crash_log)
    except Exception:
        sys.stderr.write(f"程序启动失败，请查看日志：{crash_log}\n")


def main(argv: Sequence[str] | None = None) -> int:
    startup_log = _logs_dir() / "startup.log"
    startup_log.write_text(
        f"{datetime.now().isoformat()} | version={APP_VERSION} | starting\n",
        encoding="utf-8",
    )
    try:
        return Application.from_args(list(argv) if argv is not None else sys.argv[1:]).run()
    except Exception:
        _report_fatal()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
