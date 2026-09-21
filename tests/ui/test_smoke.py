"""The --smoke-test entry point boots and verifies the whole stack."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from app import Application


def test_smoke_test_flag_exits_zero(
    tmp_home: Path,
    qapp: QApplication,
) -> None:
    exit_code = Application.from_args(["--smoke-test"]).run()
    assert exit_code == 0
