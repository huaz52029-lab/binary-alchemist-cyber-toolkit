"""PySide6 user interface layer.

Dependency direction: this package may import from ``core`` and ``app`` only.
It must never be imported by ``core``, ``modules`` or ``infrastructure``.

Core services reach the UI exclusively through ``ui.bridge`` (Qt signal bridges)
and the shared ``AppContext``; widgets never instantiate core services directly.
"""
