# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPECPATH)
icon_path = project_root / "assets" / "icon.ico"

a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "README.md"), "."),
        (str(icon_path), "assets"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FFmpegConverter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FFmpegConverter",
)
