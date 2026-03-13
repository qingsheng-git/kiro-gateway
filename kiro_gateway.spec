# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Kiro Gateway.

This spec file configures the build process for creating a standalone
Windows executable with system tray support.

Usage:
    pyinstaller kiro_gateway.spec
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files from packages
datas = []
datas += collect_data_files('tiktoken')
datas += collect_data_files('uvicorn')

# Add icon assets
datas += [
    ('assets/tray_icon.png', 'assets'),
    ('assets/tray_icon_16.png', 'assets'),
    ('assets/tray_icon_32.png', 'assets'),
    ('assets/tray_icon_warning.png', 'assets'),
    ('assets/tray_icon_warning_16.png', 'assets'),
    ('assets/tray_icon_warning_32.png', 'assets'),
    ('assets/tray_icon_error.png', 'assets'),
    ('assets/tray_icon_error_16.png', 'assets'),
    ('assets/tray_icon_error_32.png', 'assets'),
]

# Collect hidden imports
hiddenimports = []
hiddenimports += collect_submodules('uvicorn')
hiddenimports += collect_submodules('httpx')
hiddenimports += collect_submodules('pystray')
hiddenimports += [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'tiktoken_ext.openai_public',
    'tiktoken_ext',
    'pystray._win32',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'hypothesis',
        'test',
        'tests',
    ],
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
    name='KiroGateway',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window - runs in tray mode by default
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/tray_icon.ico' if os.path.exists('assets/tray_icon.ico') else None,
)
