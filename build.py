import os
import sys
import shutil
import subprocess
import venv
import re
from pathlib import Path

def get_version_from_code():
    """Nuskaito versijos numerį iš programos kodo"""
    try:
        with open('GAD manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
            version_match = re.search(r'APP_VERSION\s*=\s*["\'](.+?)["\']', content)
            if version_match:
                return version_match.group(1)
    except Exception as e:
        print(f"Nepavyko nuskaityti versijos: {e}")
    return "0.1.0"

def setup_venv():
    """Sukuria ir sukonfigūruoja virtualią aplinką jei jos nėra"""
    python_path = os.path.join('venv', 'Scripts', 'python.exe') if sys.platform == 'win32' else os.path.join('venv', 'bin', 'python')

    if os.path.exists(python_path):
        print("Naudojama esama virtuali aplinka")
        return python_path

    print("Kuriama nauja virtuali aplinka...")
    venv.create('venv', with_pip=True)

    print("Diegiami reikalingi paketai...")

    packages = [
        'pyinstaller',
        'pyqt5',
        'requests'
    ]

    for package in packages:
        print(f"Diegiamas {package}...")
        try:
            subprocess.run([python_path, '-m', 'pip', 'install', package], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Klaida diegiant {package}: {e}")
            raise

    return python_path

def create_spec_file():
    """Sukuria PyInstaller specifikacijų failą"""
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

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
"""

    with open('GADManager.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)

def main():
    """Pagrindinis kompiliavimo procesas"""
    work_dir = Path.cwd()
    print(f"Darbinis katalogas: {work_dir}")

    # Išvalome tik build ir dist katalogus
    for dir_name in ['dist', 'build']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Išvalytas {dir_name} katalogas")

    # Patikriname ar yra visi reikalingi failai
    required_files = ['GAD manager.py', 'icon.ico', 'icon.svg']
    for file in required_files:
        full_path = os.path.join(work_dir, file)
        if not os.path.exists(full_path):
            print(f"Klaida: nerastas failas {file}!")
            print(f"Ieškota: {full_path}")
            return
        else:
            print(f"Rastas failas: {file}")

    try:
        # Naudojame arba sukuriame virtualią aplinką
        python_path = setup_venv()

        # Sukuriame spec failą
        create_spec_file()
        print("Sukurtas spec failas")

        # Paleidžiame PyInstaller
        print("Pradedamas kompiliavimas...")
        subprocess.run([
            python_path,
            '-m',
            'PyInstaller',
            'GADManager.spec',
            '--clean',
            '--noconfirm'
        ], check=True)

        # Patikriname ar sukurtas exe turi reikiamus resursus
        dist_path = work_dir / 'dist' / 'GADManager'
        for file in ['icon.ico', 'icon.svg']:
            if os.path.exists(os.path.join(dist_path, file)):
                print(f"Resursas rastas dist kataloge: {file}")
            else:
                print(f"ĮSPĖJIMAS: Resursas nerastas dist kataloge: {file}")

        print("Kompiliavimas baigtas!")
        print("\nProgramos vykdomasis failas turėtų būti:", dist_path)

    except Exception as e:
        print(f"Įvyko klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
