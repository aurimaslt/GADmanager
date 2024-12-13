import os
import sys
import shutil
import subprocess
import venv
import re
import zipfile
import argparse
import time
from pathlib import Path
from typing import Optional, Tuple

def get_version_from_code() -> str:
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

def verify_required_files(work_dir: Path) -> bool:
    """Patikrina ar yra visi reikalingi failai"""
    required_files = ['GAD manager.py', 'icon.ico', 'icon.svg']
    missing_files = []

    for file in required_files:
        full_path = work_dir / file
        if not full_path.exists():
            missing_files.append(file)
            print(f"Klaida: failas {file} nerastas!")
            print(f"Ieškota: {full_path}")

    return len(missing_files) == 0

def setup_venv(requirements: Optional[list] = None) -> str:
    """Sukuria ir sukonfigūruoja virtualią aplinką"""
    python_path = os.path.join('venv', 'Scripts', 'python.exe') if sys.platform == 'win32' else os.path.join('venv', 'bin', 'python')

    if os.path.exists(python_path):
        print("Naudojama esama virtuali aplinka")
        return python_path

    print("Kuriama nauja virtuali aplinka...")
    venv.create('venv', with_pip=True)

    print("Diegiami reikalingi paketai...")
    packages = requirements or [
        'pyinstaller',
        'pyqt5',
        'requests',
        'pytest'
    ]

    # Atnaujinamas pip
    try:
        subprocess.run([python_path, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Klaida atnaujinant pip: {e}")
        raise

    for package in packages:
        print(f"Diegiamas {package}...")
        try:
            subprocess.run([python_path, '-m', 'pip', 'install', package], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Klaida diegiant {package}: {e}")
            raise

    return python_path

def clean_build_directories():
    """Išvalo build ir dist katalogus"""
    for dir_name in ['dist', 'build', '__pycache__']:
        if os.path.exists(dir_name):
            attempts = 3
            for attempt in range(attempts):
                try:
                    print(f"Valomas {dir_name} katalogas...")
                    shutil.rmtree(dir_name)
                    print(f"Išvalytas {dir_name} katalogas")
                    break
                except PermissionError:
                    if attempt < attempts - 1:
                        print(f"Klaida trinant {dir_name}, bandoma dar kartą...")
                        time.sleep(1)
                    else:
                        print(f"Nepavyko išvalyti {dir_name} katalogo po {attempts} bandymų")
                        raise
    
    # Išvalome .pyc failus
    for pyc_file in Path().rglob("*.pyc"):
        try:
            pyc_file.unlink()
        except Exception as e:
            print(f"Nepavyko ištrinti {pyc_file}: {e}")

def build_executable(python_path: str) -> bool:
    """Sukuria vykdomąjį failą su PyInstaller"""
    print("Pradedama kompiliacija...")
    try:
        subprocess.run([
            python_path,
            '-m',
            'PyInstaller',
            'GAD Manager.spec',
            '--clean',
            '--noconfirm'
        ], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller klaida: {e}")
        return False
    except Exception as e:
        print(f"Kompiliacijos klaida: {e}")
        return False

def create_release_zip(version: str, work_dir: Path) -> Path:
    """Sukuria ZIP failą GitHub išleidimui"""
    release_name = f"GADManager-v{version}"
    zip_path = work_dir / f"{release_name}.zip"
    
    # Paimame .exe iš dist katalogo
    exe_path = work_dir / 'dist' / 'GADManager' / 'GADManager.exe'
    if not exe_path.exists():
        raise FileNotFoundError(f"Vykdomasis failas nerastas: {exe_path}")
        
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Pridedame vykdomąjį failą ir visus kitus failus iš dist/GADManager katalogo
        dist_dir = work_dir / 'dist' / 'GADManager'
        for root, _, files in os.walk(dist_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = os.path.relpath(file_path, dist_dir)
                zipf.write(file_path, arcname)
        
        # Pridedame ikonų failus
        for icon_file in ['icon.ico', 'icon.svg']:
            icon_path = work_dir / icon_file
            if icon_path.exists():
                zipf.write(icon_path, icon_file)
    
    return zip_path

def main():
    """Pagrindinis build procesas"""
    work_dir = Path.cwd()
    print(f"Darbinis katalogas: {work_dir}")
    
    # Automatiškai išvalome prieš kiekvieną build'ą
    print("\nPradedamas aplinkos valymas...")
    clean_build_directories()
    print("Aplinkos valymas baigtas\n")

    # Gauname programos versiją
    version = get_version_from_code()
    print(f"Kompiliuojama versija: {version}")

    try:
        # Sukonfigūruojame virtualią aplinką
        python_path = setup_venv()

        # Patikriname reikalingus failus
        if not verify_required_files(work_dir):
            sys.exit(1)

        # Sukuriame vykdomąjį failą
        if not build_executable(python_path):
            sys.exit(1)

        # Sukuriame ZIP 
        zip_path = create_release_zip(version, work_dir)
        print(f"\nSukurtas ZIP failas: {zip_path}")

        print("\nKompiliacija sėkmingai baigta!")
        print("\nDabar galite įkelti failus į GitHub.")

    except Exception as e:
        print(f"Įvyko klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()