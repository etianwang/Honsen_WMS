# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — React 桌面版（pywebview + FastAPI + 静态前端）

import sys
from pathlib import Path

block_cipher = None
root = Path(SPEC).resolve().parent.parent
frontend_out = root / "frontend" / "out"
icon_path = root / "logo.ico"

if not (frontend_out / "index.html").exists():
    raise SystemExit("请先构建前端：cd frontend && npm run build:desktop")

if not icon_path.is_file():
    raise SystemExit(f"未找到应用图标：{icon_path}")

datas = [
    (str(frontend_out), "frontend/out"),
]

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "backend.main",
    "backend.routers.auth",
    "backend.routers.config",
    "backend.routers.data",
    "backend.routers.health",
    "backend.routers.inventory",
    "backend.routers.system",
    "backend.routers.transactions",
    "db_manager",
    "data_utility",
]

a = Analysis(
    [str(root / "desktop" / "launcher.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Honsen WMS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
)
