# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec for the Binary Alchemist Cyber Toolkit.

Shipped resources (configs, themes, icons) are resolved at runtime relative to
the executable directory, so they are collected next to the executable rather
than inside the ``_internal`` bundle.
"""

from PyInstaller.utils.hooks import copy_metadata


def _filter_binaries(binaries):
    """Drop environment-specific and OS-provided DLLs from the bundle.

    PyInstaller resolves binary dependencies through PATH, which can pull in
    mismatched copies of ICU / OpenSSL / UCRT from unrelated toolchains (for
    example a Codex runtime cache). Those shadow the operating system copies
    and break Qt's DLL loading, so they must never ship.
    """
    blocked_names = {"ucrtbase.dll"}
    filtered = []
    for name, path, kind in binaries:
        if name.lower() in blocked_names:
            continue
        if name.lower().startswith("api-ms-win-"):
            continue
        if "codex-runtimes" in path.lower():
            continue
        filtered.append((name, path, kind))
    return filtered


datas = [
    ("configs", "configs"),
    ("resources", "resources"),
]
datas += copy_metadata("binary-alchemist-cyber-toolkit")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
a.binaries = _filter_binaries(a.binaries)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BinaryAlchemist",
    contents_directory=".",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BinaryAlchemist",
)
