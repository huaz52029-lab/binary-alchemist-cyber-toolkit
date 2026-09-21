"""Thin entry point; all real work lives in :mod:`app`."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from app import Application


def main(argv: Sequence[str] | None = None) -> int:
    return Application.from_args(list(argv) if argv is not None else sys.argv[1:]).run()


if __name__ == "__main__":
    raise SystemExit(main())
