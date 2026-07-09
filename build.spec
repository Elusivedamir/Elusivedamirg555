# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

hiddenimports = (
    collect_submodules('telethon')
    + collect_submodules('qasync')
    + collect_submodules('keyring')
    + collect_submodules('PyQt6')
    + ['socks']
)

datas = []
datas += collect_data_files('telethon', include_py_files=True)
datas += collect_data_files('PyQt6')
datas += collect_data_files('keyring')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TelegramAutoBot',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='TelegramAutoBot',
)

app = BUNDLE(
    coll,
    name='TelegramAutoBot.app',
    icon=None,
    bundle_identifier='com.telegramautobot.app',
    info_plist={
        'CFBundleName': 'TelegramAutoBot',
        'CFBundleDisplayName': 'TelegramAutoBot',
        'CFBundleIdentifier': 'com.telegramautobot.app',
        'LSBackgroundOnly': False,
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
    },
)
