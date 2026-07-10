# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

pyqt6_datas, pyqt6_binaries, pyqt6_hiddenimports = collect_all('PyQt6')

a = Analysis(
    ['login.py'],
    pathex=[],
    binaries=pyqt6_binaries,
    datas=[
        ('logo.png', '.'),
        ('wechat_qr.png', '.'),
        ('github.svg', '.'),
        ('telegram.svg', '.'),
        ('wechat.svg', '.'),
        ('theme/theme.qss', 'theme'),
    ] + pyqt6_datas,
    hiddenimports=pyqt6_hiddenimports + ['theme.loader'],
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
    a.binaries,
    a.datas,
    [],
    name='Honsen WMS',
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
    icon=['logo.ico'],
)
