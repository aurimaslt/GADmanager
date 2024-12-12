# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_all, copy_metadata

block_cipher = None

# Reikalingi failai ir resursai
added_files = [
    (os.path.abspath('icon.ico'), '.'),
    (os.path.abspath('icon.svg'), '.')
]

# Reikalingi PyQt5 moduliai
qt_modules = [
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets'
]

# Surenkame tik reikalingas PyQt5 priklausomybes
datas = added_files.copy()
binaries = []

# Įtraukiame visus reikalingus hiddenimports
hiddenimports = [
    'PyQt5.sip',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets'
]

# Pridedame PyQt5 metaduomenis
datas += copy_metadata('PyQt5')

# Surenkame PyQt5 modulius
for module in qt_modules:
    imports = collect_all(module)
    datas.extend(imports[0])
    binaries.extend(imports[1])
    hiddenimports.extend(imports[2])

a = Analysis(
    ['GAD manager.py'],
    pathex=[os.path.abspath(os.getcwd())],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5.QtWebEngine',
        'PyQt5.QtWebEngineCore',
        'PyQt5.QtMultimedia',
        'PyQt5.QtNetwork',
        'PyQt5.QtBluetooth',
        'PyQt5.QtDBus',
        'PyQt5.QtDesigner',
        'PyQt5.QtHelp',
        'PyQt5.QtLocation',
        'PyQt5.QtMultimediaWidgets',
        'PyQt5.QtNfc',
        'PyQt5.QtOpenGL',
        'PyQt5.QtPositioning',
        'PyQt5.QtQml',
        'PyQt5.QtQuick',
        'PyQt5.QtQuickWidgets',
        'PyQt5.QtSensors',
        'PyQt5.QtSerialPort',
        'PyQt5.QtSql',
        'PyQt5.QtTest',
        'PyQt5.QtWebChannel',
        'PyQt5.QtWebSockets',
        'PyQt5.QtXml',
        'PyQt5.QtXmlPatterns'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

# Šaliname nereikalingus Qt plugins
excluded_plugins = [
    'qt5webkit',
    'qt5quick',
    'qt53d',
    'platformthemes',
    'audio',
    'mediaservice',
    'playlistformats',
    'position',
    'renderplugins',
    'sceneparsers',
    'sensors',
    'sensorgestures',
    'sqldrivers',
    'texttospeech',
    'webview'
]

for plugin in excluded_plugins:
    for item in a.binaries.copy():
        if plugin in item[0].lower():
            a.binaries.remove(item)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GADManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.abspath('icon.ico'),
    uac_admin=False
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GADManager'
)
