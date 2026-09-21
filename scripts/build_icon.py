"""Regenerate ``resources/icons/app.ico`` from ``app.svg``.

Requires the offscreen Qt platform; renders several resolutions and packs them
into one PNG-based ICO container so Windows Explorer shows a sharp icon at
every size. The generated file is checked into the repository.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSize
from PySide6.QtGui import QImage, QImageWriter, QPainter
from PySide6.QtSvg import QSvgRenderer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = PROJECT_ROOT / "resources" / "icons" / "app.svg"
ICO_PATH = PROJECT_ROOT / "resources" / "icons" / "app.ico"
SIZES = (256, 128, 64, 48, 32, 16)


def _render_png(size: int) -> bytes:
    renderer = QSvgRenderer(str(SVG_PATH))
    image = QImage(QSize(size, size), QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    QImageWriter(buffer, QByteArray(b"PNG")).write(image)
    return bytes(buffer.data().data())


def _pack_ico(images: dict[int, bytes]) -> bytes:
    entries = []
    payload = bytearray()
    offset = 6 + 16 * len(images)
    for size, png in sorted(images.items(), reverse=True):
        payload += png
        entries.append(
            struct.pack(
                "<BBBBHHII",
                size % 256,
                size % 256,
                0,
                0,
                1,
                32,
                len(png),
                offset,
            )
        )
        offset += len(png)
    header = struct.pack("<HHH", 0, 1, len(images))
    return header + b"".join(entries) + bytes(payload)


def main() -> int:
    if not SVG_PATH.is_file():
        print(f"missing icon source: {SVG_PATH}")
        return 1
    images = {size: _render_png(size) for size in SIZES}
    ICO_PATH.write_bytes(_pack_ico(images))
    print(f"wrote {ICO_PATH} ({ICO_PATH.stat().st_size} bytes, {len(SIZES)} sizes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
