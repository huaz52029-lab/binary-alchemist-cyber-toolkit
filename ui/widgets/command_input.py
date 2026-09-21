"""Labeled single/multi-line input with a validation state."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget


class CommandInput(QWidget):
    """A labeled input field (line edit or plain text) with validation feedback."""

    text_changed = Signal(str)

    MODE_SINGLE = "single"
    MODE_MULTI = "multi"

    def __init__(
        self,
        *,
        label: str = "",
        placeholder: str = "",
        mode: str = MODE_SINGLE,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("commandInput")
        self._mode = mode
        self._label = QLabel(label, self)
        self._label.setVisible(bool(label))
        self._editor: QLineEdit | QPlainTextEdit
        editor: QLineEdit | QPlainTextEdit
        if mode == self.MODE_MULTI:
            plain = QPlainTextEdit(self)
            plain.setMinimumHeight(96)
            plain.textChanged.connect(lambda: self.text_changed.emit(plain.toPlainText()))
            editor = plain
        else:
            line = QLineEdit(self)
            line.textChanged.connect(self.text_changed)
            editor = line
        editor.setObjectName("commandInputEditor")
        editor.setPlaceholderText(placeholder)
        self._editor = editor
        self._state_label = QLabel("", self)
        self._state_label.setObjectName("commandInputState")
        self._state_label.setVisible(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self._label)
        layout.addWidget(editor)
        layout.addWidget(self._state_label)

    def text(self) -> str:
        if isinstance(self._editor, QPlainTextEdit):
            return self._editor.toPlainText()
        return self._editor.text()

    def set_text(self, value: str) -> None:
        if isinstance(self._editor, QPlainTextEdit):
            self._editor.setPlainText(value)
        else:
            self._editor.setText(value)

    def clear(self) -> None:
        self.set_text("")

    def set_label(self, label: str) -> None:
        self._label.setText(label)
        self._label.setVisible(bool(label))

    def set_placeholder(self, placeholder: str) -> None:
        self._editor.setPlaceholderText(placeholder)

    def set_validation(self, state: str | None, message: str = "") -> None:
        """Show a valid/invalid border and an optional hint.

        ``state`` is one of ``"valid"``, ``"invalid"`` or ``None`` (neutral).
        """
        if state not in (None, "valid", "invalid"):
            raise ValueError(f"invalid validation state: {state}")
        self._editor.setProperty("validation", state or "normal")
        editor_style = self._editor.style()
        editor_style.unpolish(self._editor)
        editor_style.polish(self._editor)
        self._state_label.setText(message)
        self._state_label.setVisible(bool(message))

    def editor(self) -> QWidget:
        return self._editor
