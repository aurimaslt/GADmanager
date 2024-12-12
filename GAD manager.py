################################
# Version info
################################
APP_VERSION = "0.22 beta"
APP_RELEASE_DATE = "2024-12-12"
################################
import os
os.environ['QT_PLUGIN_PATH'] = 'C:/Users/AurimasLesmanavičius/AppData/Roaming/Python/Python312/site-packages/PyQt5/Qt5/plugins'
import sys
import re
import tempfile
import requests
import hashlib
from datetime import datetime
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor

@dataclass
class GithubReleaseInfo:
    """GitHub Release information structure"""
    version: str
    release_date: str
    download_url: str
    changelog: str
    is_prerelease: bool

@dataclass
class StorageSystem:
    """Saugyklos sistemos informacija"""
    serial_number: str
    host: str
    ldev_number: str
    status: str
    role: str
    rw_status: str
    instance: str

@dataclass
class GADPair:
    """GAD porų informacija"""
    group: str
    name: str
    left_storage: StorageSystem
    right_storage: StorageSystem

class GadStatus(Enum):
    PAIR = "PAIR"      # Sinchronizuota pora
    PSUS = "PSUS"      # Sustabdyta nuo pirminės pusės
    SSUS = "SSUS"      # Sustabdyta nuo antrinės pusės
    SSWS = "SSWS"      # Sustabdyta, antrinė pusė priima įrašymus
    PSUE = "PSUE"      # Sustabdyta dėl klaidos
    COPY = "COPY"      # Vyksta kopijavimas

class ProStyle:
    """Aplikacijos stiliaus apibrėžimai"""
    STYLE = """
    QMainWindow {
        background-color: #f0f2f5;
    }
    QFrame {
        background-color: white;
        border: none;
        border-radius: 6px;
    }
    QLabel {
        color: #1a1f36;
    }
    QPushButton {
        background-color: #f7f9fc;
        border: 1px solid #d0d5dd;
        border-radius: 4px;
        color: #344054;
        padding: 6px 12px;
        font-weight: 500;
        min-width: 80px;
    }
    QPushButton:hover {
        background-color: #ffffff;
        border-color: #9da5b4;
    }
    QPushButton:pressed {
        background-color: #f0f2f5;
    }
    QPushButton[class="primary"] {
        background-color: #0052cc;
        border: 1px solid #0052cc;
        color: white;
    }
    QPushButton[class="primary"]:hover {
        background-color: #0747a6;
        border-color: #0747a6;
    }
    QPushButton[disabled="true"] {
        background-color: #f0f2f5 !important;
        border-color: #d0d5dd !important;
        color: #9da5b4 !important;
        cursor: not-allowed;
    }
    QTextEdit {
        border: 1px solid #d0d5dd;
        border-radius: 4px;
        padding: 4px;
        background: white;
    }
    QStatusBar {
        background: white;
        color: #666;
    }
    """

    STATUS_COLORS = {
        'PAIR': '#00875a',
        'PSUS': '#ff8800',
        'SSUS': '#ff8800',
        'SSWS': '#ff8800',
        'PSUE': '#de350b',
        'COPY': '#0052cc'
    }

    RW_STATUS_COLORS = {
        'L/M': '#00875a',
        'L/L': '#0052cc',
        'B/B': '#de350b'
    }
class UpdateController:
    """Atnaujinimų valdymo kontroleris"""
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.app_version = APP_VERSION
        self.init_auto_updater()
        
    def init_auto_updater(self):
        """Inicializuoja auto-updater"""
        self.auto_updater = GithubAutoUpdater(
            self.app_version,
            "aurimaslt",
            "GADmanager"
        )
    
    def check_for_updates(self) -> bool:
        """Patikrina ar yra atnaujinimų"""
        return self.auto_updater.check_and_update(self.parent_window)

class GithubUpdateChecker:
    """Checks for available updates using GitHub API"""
    def __init__(self, current_version: str, repo_owner: str, repo_name: str):
        self.current_version = current_version
        self.api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases"
        
    def _parse_version(self, version: str) -> tuple:
        """Converts version string to comparable tuple"""
        version = version.split(' ')[0]
        return tuple(map(int, version.split('.')))
    
    def check_for_updates(self) -> Optional[GithubReleaseInfo]:
        """Checks if a new version is available on GitHub"""
        try:
            headers = {'Accept': 'application/vnd.github.v3+json'}
            response = requests.get(self.api_url, headers=headers, timeout=5)
            response.raise_for_status()
            
            releases = response.json()
            if not releases:
                return None
                
            latest_release = releases[0]
            latest_version = latest_release['tag_name'].lstrip('v')
            
            if self._parse_version(latest_version) > self._parse_version(self.current_version):
                zip_asset = next(
                    (asset for asset in latest_release['assets'] 
                     if asset['name'].endswith('.zip')),
                    None
                )
                
                if not zip_asset:
                    return None
                    
                return GithubReleaseInfo(
                    version=latest_version,
                    release_date=latest_release['published_at'].split('T')[0],
                    download_url=zip_asset['browser_download_url'],
                    changelog=latest_release['body'],
                    is_prerelease=latest_release['prerelease']
                )
            return None
            
        except Exception as e:
            print(f"Error checking for updates: {e}")
            return None

class UpdateDownloader(QThread):
    """Downloads updates in a separate thread"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, url: str, save_path: str):
        super().__init__()
        self.url = url
        self.save_path = save_path
        
    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            downloaded = 0
            
            with open(self.save_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    if total_size:
                        progress = int((downloaded / total_size) * 100)
                        self.progress.emit(progress)
                        
            self.finished.emit(True, "")
            
        except Exception as e:
            self.finished.emit(False, str(e))

class UpdateDialog(QDialog):
    """Update progress dialog"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Software Update")
        self.setModal(True)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("Downloading update...")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
        
    def update_progress(self, value: int):
        self.progress_bar.setValue(value)
        
    def set_status(self, text: str):
        self.status_label.setText(text)
        
class GithubAutoUpdater:
    """Main GitHub-based auto-update controller"""
    def __init__(self, app_version: str, repo_owner: str, repo_name: str):
        self.app_version = app_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(os.path.expanduser("~"), ".gadmanager", "backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        
    def check_and_update(self, parent=None) -> bool:
        """Checks for updates and performs update if available"""
        checker = GithubUpdateChecker(self.app_version, self.repo_owner, self.repo_name)
        release_info = checker.check_for_updates()
        
        if not release_info:
            return False
            
        prerelease_warning = "\n\nNOTE: This is a pre-release version!" if release_info.is_prerelease else ""
            
        response = QMessageBox.question(
            parent,
            "Update Available",
            f"Version {release_info.version} is available.\n\n"
            f"Release Date: {release_info.release_date}\n\n"
            f"Changelog:\n{release_info.changelog}\n"
            f"{prerelease_warning}\n\n"
            "Would you like to update now?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if response == QMessageBox.Yes:
            return self._perform_update(release_info, parent)
            
        return False
    
    def _perform_update(self, release_info: GithubReleaseInfo, parent) -> bool:
        """Performs the actual update process"""
        dialog = UpdateDialog(parent)
        
        # Download update
        temp_file = os.path.join(self.temp_dir, "update.zip")
        downloader = UpdateDownloader(release_info.download_url, temp_file)
        
        downloader.progress.connect(dialog.update_progress)
        downloader.finished.connect(lambda success, error: self._handle_download_finished(
            success, error, dialog, temp_file
        ))
        
        downloader.start()
        result = dialog.exec_()
        
        if result == QDialog.Rejected:
            downloader.terminate()
            return False
            
        return True
    
    def _handle_download_finished(self, success: bool, error: str, 
                                dialog: UpdateDialog, temp_file: str):
        """Handles download completion"""
        if not success:
            QMessageBox.critical(dialog, "Error", f"Download failed: {error}")
            dialog.reject()
            return
            
        dialog.set_status("Installing update...")
        
        installer = UpdateInstaller(self.temp_dir, self.backup_dir)
        
        if installer.install_update(temp_file):
            QMessageBox.information(
                dialog,
                "Update Complete",
                "The update has been installed successfully.\n"
                "Please restart the application to apply the changes."
            )
            dialog.accept()
        else:
            QMessageBox.critical(
                dialog,
                "Update Failed",
                "Failed to install the update.\n"
                "The previous version has been restored."
            )
            dialog.reject()

class UpdateInstaller:
    """Handles the update installation process"""
    def __init__(self, temp_dir: str, backup_dir: str):
        self.temp_dir = temp_dir
        self.backup_dir = backup_dir
        
    def backup_current_version(self):
        """Creates backup of current version"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}")
        os.makedirs(backup_path, exist_ok=True)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        for file in os.listdir(current_dir):
            if file.endswith(('.py', '.svg', '.exe')):
                src_path = os.path.join(current_dir, file)
                dst_path = os.path.join(backup_path, file)
                if os.path.isfile(src_path):
                    with open(src_path, 'rb') as src, open(dst_path, 'wb') as dst:
                        dst.write(src.read())
                        
        return backup_path
    
    def install_update(self, update_file: str) -> bool:
        """Installs the update"""
        try:
            backup_path = self.backup_current_version()
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            import zipfile
            with zipfile.ZipFile(update_file, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
                
                for file in os.listdir(self.temp_dir):
                    src_path = os.path.join(self.temp_dir, file)
                    dst_path = os.path.join(current_dir, file)
                    if os.path.isfile(src_path):
                        with open(src_path, 'rb') as src, open(dst_path, 'wb') as dst:
                            dst.write(src.read())
            
            return True
            
        except Exception as e:
            print(f"Error installing update: {e}")
            self.rollback(backup_path)
            return False
    
    def rollback(self, backup_path: str):
        """Rolls back to backup if update fails"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        for file in os.listdir(backup_path):
            src_path = os.path.join(backup_path, file)
            dst_path = os.path.join(current_dir, file)
            if os.path.isfile(src_path):
                with open(src_path, 'rb') as src, open(dst_path, 'wb') as dst:
                    dst.write(src.read())

class GADController:
    """GAD porų valdymo kontroleris"""
    def __init__(self):
        self.pairs = []
        self.copy_controller = CopyProgress()

    def update_pairs(self, new_pairs: List[GADPair]):
        """Atnaujina porų informaciją"""
        self.pairs = new_pairs
        
    def get_command_for_operation(self, pair: GADPair, operation: str) -> str:
        """Generuoja komandą pagal operacijos tipą"""
        commands = {
            "split_vsp1": f"pairsplit -g {pair.group} {pair.left_storage.instance}",
            "split_vsp2": f"pairsplit -g {pair.group} -RS {pair.right_storage.instance}",
            "swap_p": f"pairresync -g {pair.group} -swaps {pair.right_storage.instance}",
            "swap_s": f"pairresync -g {pair.group} -swaps {pair.left_storage.instance}",
            "resync": self.get_resync_command(pair)
        }
        return commands.get(operation, "Unknown command")

    def get_resync_command(self, pair: GADPair) -> str:
        """Generuoja resync komandą"""
        if (pair.right_storage.role == 'S-VOL' and
            pair.right_storage.status == 'SSWS' and
            pair.left_storage.role == 'P-VOL' and
            pair.left_storage.status == 'PSUS'):
            return (f"pairresync -g {pair.group} -swaps -IH20\n"
                   f"pairresync -g {pair.group} -swaps -IH10")
        elif (pair.left_storage.role == 'S-VOL' and
              pair.left_storage.status == 'SSWS' and
              pair.right_storage.role == 'P-VOL' and
              pair.right_storage.status == 'PSUS'):
            return (f"pairresync -g {pair.group} -swaps -IH10\n"
                   f"pairresync -g {pair.group} -IH10")
        elif (pair.left_storage.role == 'P-VOL' and
              pair.left_storage.status == 'PSUS' and
              pair.right_storage.role == 'S-VOL' and
              pair.right_storage.status == 'SSUS'):
            return f"pairresync -g {pair.group} -IH10"
        else:
            return "# Cannot perform resync - invalid pair state"

class CopyProgress:
    """Klasė kopijavimo progreso valdymui"""
    def __init__(self):
        self.progress = {}

    def update_progress(self, pair_id: str, progress: int):
        """Atnaujina kopijavimo progresą konkrečiai porai"""
        self.progress[pair_id] = {
            'progress': progress,
            'time': datetime.now()
        }

    def get_estimated_end_time(self, pair_id: str) -> Optional[datetime]:
        """Apskaičiuoja numatomą kopijavimo pabaigos laiką"""
        if pair_id not in self.progress:
            return None

        current = self.progress[pair_id]
        if len(self.progress) < 2:
            return None

        rate = current['progress'] / (datetime.now() - current['time']).seconds
        remaining_progress = 100 - current['progress']

        if rate > 0:
            remaining_time = remaining_progress / rate
            return datetime.now() + timedelta(seconds=remaining_time)
        return None

    def get_copy_status(self, pair_id: str) -> dict:
        """Gauna detalią kopijavimo būsenos informaciją"""
        if pair_id not in self.progress:
            return {
                'status': 'UNKNOWN',
                'progress': 0,
                'estimated_end_time': None
            }

        progress = self.progress[pair_id]['progress']
        return {
            'status': 'COPYING' if progress < 100 else 'COMPLETED',
            'progress': progress,
            'estimated_end_time': self.get_estimated_end_time(pair_id)
        }

class StorageView(QFrame):
    """Saugyklos informacijos atvaizdavimo komponentas"""
    def __init__(self, storage_num, storage: StorageSystem = None):
        super().__init__()
        self.storage = storage
        self.init_ui(storage_num)

    def init_ui(self, num):
        layout = QGridLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 4, 8, 4)

        # Header
        self.header = QLabel(f"VSP {num}")
        self.header.setStyleSheet("font-size: 13px; font-weight: bold; color: #1a1f36;")
        layout.addWidget(self.header, 0, 0, 1, 2)

        # Status indicators
        self.status = QLabel("● PAIR")
        self.status.setStyleSheet(f"color: {ProStyle.STATUS_COLORS['PAIR']}; font-weight: 500;")
        layout.addWidget(self.status, 1, 0)

        # Latest data indicator
        self.latest_data = QLabel()
        self.latest_data.setStyleSheet("font-weight: bold; color: #00875a;")
        layout.addWidget(self.latest_data, 1, 1, Qt.AlignRight)

        # Info grid
        self.labels = {}
        self.values = {}
        info_fields = ["LDEV:", "Role:", "R/W:", "Instance:"]

        for row, field in enumerate(info_fields, start=2):
            label = QLabel(field)
            label.setStyleSheet("color: #666;")
            value = QLabel("-")
            value.setStyleSheet("color: #1a1f36; font-weight: 500;")

            layout.addWidget(label, row, 0)
            layout.addWidget(value, row, 1)

            self.labels[field] = label
            self.values[field] = value

        if self.storage:
            self.update_storage(self.storage)

    def determine_latest_data(self, storage: StorageSystem) -> bool:
        """Nustatoma ar šioje pusėje yra naujausi duomenys"""
        if storage.status == 'PSUS' and storage.rw_status == 'B/B':
            return False
        if storage.status == 'SSWS' and storage.rw_status == 'L/L':
            return True
        if storage.status == 'PAIR':
            return True
        if storage.status in ['COPY', 'INIT']:
            return storage.role == 'P-VOL'
        if storage.status in ['PSUS', 'SSUS']:
            return storage.role == 'P-VOL'
        if storage.status == 'PSUE':
            if storage.rw_status == 'B/B':
                return True
            else:
                return storage.role == 'P-VOL'
        return False

    def update_storage(self, storage: StorageSystem):
        """Atnaujina saugyklos informaciją"""
        self.storage = storage
        self.header.setText(f"VSP ({storage.serial_number})")

        # Atnaujina statusą su spalva
        status_color = ProStyle.STATUS_COLORS.get(storage.status, '#666')
        self.status.setText(f"● {storage.status}")
        self.status.setStyleSheet(f"color: {status_color}; font-weight: 500;")

        # Atnaujina "Latest Data" indikatorių
        has_latest = self.determine_latest_data(storage)
        if has_latest:
            if storage.status == 'PAIR' or (storage.status == 'PSUE' and storage.rw_status == 'B/B'):
                self.latest_data.setText("✓ Synced Data")
            else:
                self.latest_data.setText("✓ Latest Data")
            self.latest_data.setVisible(True)
        else:
            self.latest_data.setVisible(False)

        # Atnaujina kitus laukus
        self.values["LDEV:"].setText(storage.ldev_number)
        self.values["Role:"].setText(storage.role)

        # R/W statusas su spalva
        rw_color = ProStyle.RW_STATUS_COLORS.get(storage.rw_status, '#666')
        self.values["R/W:"].setText(storage.rw_status)
        self.values["R/W:"].setStyleSheet(f"color: {rw_color}; font-weight: 500;")

        self.values["Instance:"].setText(storage.instance)

class GadPairPanel(QFrame):
    """GAD poros valdymo panelis"""
    def __init__(self, pair: GADPair = None):
        super().__init__()
        self.pair = pair
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 4, 8, 4)

        # Header with pair name
        self.header = QLabel(self.pair.name if self.pair else "GAD Pair")
        self.header.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1f36;")
        layout.addWidget(self.header)

        # Storage views in horizontal layout
        storage_layout = QHBoxLayout()
        storage_layout.setSpacing(4)
        self.left_storage = StorageView(1, self.pair.left_storage if self.pair else None)
        self.right_storage = StorageView(2, self.pair.right_storage if self.pair else None)
        storage_layout.addWidget(self.left_storage)
        storage_layout.addWidget(self.right_storage)
        layout.addLayout(storage_layout)

        # Action buttons
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(2)
        self.buttons = {}

        button_configs = [
            ("split_vsp1", "Split VSP1"),
            ("split_vsp2", "Split VSP2"),
            ("swap_p", "Swap P→S"),
            ("swap_s", "Swap S→P"),
            ("resync", "Resync")
        ]

        for btn_id, text in button_configs:
            btn = QPushButton(text)
            btn.setEnabled(False)
            self.buttons[btn_id] = btn
            self.button_layout.addWidget(btn)

        layout.addLayout(self.button_layout)

        if self.pair:
            self.update_button_states()

    def update_pair(self, pair: GADPair):
        """Atnaujina poros informaciją"""
        self.pair = pair
        self.header.setText(f"{pair.group} - {pair.name}")
        self.left_storage.update_storage(pair.left_storage)
        self.right_storage.update_storage(pair.right_storage)
        self.update_button_states()

    def update_button_states(self):
        if not self.pair:
            return

        # Reset buttons
        for btn in self.buttons.values():
            btn.setEnabled(False)
            btn.setProperty("class", "")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f7f9fc;
                    border: 1px solid #d0d5dd;
                    border-radius: 4px;
                    color: #344054;
                    padding: 6px 12px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #ffffff;
                    border-color: #9da5b4;
                }
            """)

        # Check pair synchronization state
        is_synchronized = (
            self.pair.left_storage.status == 'PAIR' and
            self.pair.right_storage.status == 'PAIR'
        )

        # Split buttons
        if is_synchronized:
            self.buttons["split_vsp1"].setEnabled(True)
            self.buttons["split_vsp2"].setEnabled(True)
            self._set_active_button_style(self.buttons["split_vsp1"])
            self._set_active_button_style(self.buttons["split_vsp2"])

        # Swap buttons
        can_swap_p_to_s = (is_synchronized and
                          self.pair.left_storage.role == 'P-VOL' and
                          self.pair.right_storage.role == 'S-VOL')
        can_swap_s_to_p = (is_synchronized and
                          self.pair.left_storage.role == 'S-VOL' and
                          self.pair.right_storage.role == 'P-VOL')

        if can_swap_p_to_s:
            self.buttons["swap_p"].setEnabled(True)
            self._set_active_button_style(self.buttons["swap_p"])
        if can_swap_s_to_p:
            self.buttons["swap_s"].setEnabled(True)
            self._set_active_button_style(self.buttons["swap_s"])

        # Resync button
        can_resync = (
            (self.pair.right_storage.role == 'S-VOL' and
             self.pair.right_storage.status == 'SSWS' and
             self.pair.left_storage.role == 'P-VOL' and
             self.pair.left_storage.status == 'PSUS') or
            (self.pair.left_storage.role == 'S-VOL' and
             self.pair.left_storage.status == 'SSWS' and
             self.pair.right_storage.role == 'P-VOL' and
             self.pair.right_storage.status == 'PSUS') or
            (self.pair.left_storage.role == 'P-VOL' and
             self.pair.left_storage.status == 'PSUS' and
             self.pair.right_storage.role == 'S-VOL' and
             self.pair.right_storage.status == 'SSUS') or
            (self.pair.right_storage.status == 'SSWS' and
             self.pair.right_storage.role == 'P-VOL' and
             self.pair.left_storage.status == 'PSUS' and
             self.pair.left_storage.role == 'S-VOL')
        )

        if can_resync:
            self.buttons["resync"].setEnabled(True)
            self._set_active_button_style(self.buttons["resync"])

    def _set_active_button_style(self, button: QPushButton):
        """Sets the active (primary) style for enabled buttons"""
        button.setStyleSheet("""
            QPushButton {
                background-color: #0052cc;
                border: 1px solid #0052cc;
                border-radius: 4px;
                color: white;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #0747a6;
                border-color: #0747a6;
            }
            QPushButton:pressed {
                background-color: #0747a6;
            }
        """)

class OutputParserFrame(QWidget):
    """Output parser widget"""
    def __init__(self, parent=None, callback=None):
        super().__init__(parent)
        self.callback = callback
        self.cmd_output = None
        self.init_ui()
        self.debug = True

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)

        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("To get the required output:\n"
                                     "1. SSH into your server\n"
                                     "2. Run command (click button to copy):\n"
                                     "3. Replace GROUP with your GAD group name\n"
                                     "4. Paste pairdisplay output here...")
        self.input_field.setMaximumHeight(80)
        layout.addWidget(self.input_field)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        
        # Komanda ir Copy mygtukas
        cmd_label = QLabel("pairdisplay -g GROUP -CLI -IH10")
        cmd_label.setStyleSheet("font-family: monospace; padding: 4px; color: #0052cc;")
        button_layout.addWidget(cmd_label)
        
        copy_btn = QPushButton("📋 Copy Pairdisplay")
        copy_btn.setFixedWidth(150)
        copy_btn.clicked.connect(lambda: self.copy_command())
        button_layout.addWidget(copy_btn)
        
        button_layout.addSpacing(10)
        
        # Kiti mygtukai
        help_btn = QPushButton("❓ Show Example")
        help_btn.clicked.connect(self.show_example)
        button_layout.addWidget(help_btn)

        parse_btn = QPushButton("📝 Parse Input")
        parse_btn.clicked.connect(lambda: self.parse_output(self.input_field.toPlainText()))
        button_layout.addWidget(parse_btn)

        paste_btn = QPushButton("📋 Parse from Clipboard")
        paste_btn.setProperty("class", "primary")
        paste_btn.clicked.connect(lambda: self.parse_clipboard(True))
        button_layout.addWidget(paste_btn)
        
        button_layout.addStretch(1)
        layout.addLayout(button_layout)

    def copy_command(self):
        QApplication.clipboard().setText("pairdisplay -g GROUP -CLI -IH10")
        QMessageBox.information(self, "Success", "Command copied to clipboard!")

    def set_command_output(self, cmd_output):
        self.cmd_output = cmd_output

    def show_example(self):
        msg = QMessageBox()
        msg.setWindowTitle("Example Output")
        msg.setText("Example of the expected pairdisplay output format:")
        
        example = """Group   PairVol(L/R) (Port#,TID, LU),Seq#,LDEV#.P/S,Status,Fence,   %,P-LDEV# M CTG JID AP EM       E-Seq# E-LDEV# R/W QM DM P PR CS D_Status ST ELV PGID           CT(s) LUT
HDID    GAD_TEST_HA(L) (CL8-F-8, 0,   5)811111  6001.P-VOL PSUS NEVER ,  100  6001 -   -   0  4  -            -       - B/B -  D  N D   3 -         - -      -               - -
HDID    GAD_TEST_HA(R) (CL8-F-12, 0,   5)822222  6001.S-VOL SSWS NEVER ,  100  6001 -   -   0  4  -            -       - L/L -  D  N D   3 -         - -      -               - -
Group   PairVol(L/R) (Port#,TID, LU),Seq#,LDEV#.P/S,Status,Fence,   %,P-LDEV# M CTG JID AP EM       E-Seq# E-LDEV# R/W QM DM P PR CS D_Status ST ELV PGID           CT(s) LUT
HDID    GAD_TEST_HA(L) (CL8-F-8, 0,   5)811111  6001.P-VOL PSUS NEVER ,  100  6001 -   -   0  4  -            -       - B/B -  D  N D   3 -         - -      -               - -
HDID    GAD_TEST_HA(R) (CL8-F-12, 0,   5)822222  6001.S-VOL SSWS NEVER ,  100  6001 -   -   0  4  -            -       - L/L -  D  N D   3 -         - -      -               - -
HDID2    GAD_TEST_HA2(L) (CL8-F-8, 0,   5)811111  6002.P-VOL PAIR NEVER ,  100  6002 -   -   0  4  -            -       - L/L -  D  N D   3 -         - -      -               - -
HDID2    GAD_TEST_HA2(R) (CL8-F-12, 0,   5)822222  6002.S-VOL PAIR NEVER ,  100  6002 -   -   0  4  -            -       - L/L -  D  N D   3 -         - -      -               - -"""
      
        text_edit = QTextEdit()
        text_edit.setPlainText(example)
        text_edit.setReadOnly(True)
        text_edit.setMinimumWidth(850)
        text_edit.setMinimumHeight(10)
        
        layout = msg.layout()
        layout.addWidget(text_edit, 1, 0, 1, layout.columnCount())
        msg.exec_()

    def log(self, msg: str):
        if self.debug:
            print(f"DEBUG: {msg}")

    def parse_clipboard(self, clear_input=False):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if not text:
            QMessageBox.warning(self, "Error", "Clipboard is empty")
            return
        if clear_input:
            self.input_field.setText(text)
        self.parse_output(text)

    def parse_output(self, text: str):
        if not text:
            QMessageBox.warning(self, "Error", "Please enter pairdisplay output")
            return

        try:
            self.log(f"Starting text analysis:\n{text}")
            pairs = self._parse_pairdisplay(text)
            if self.callback:
                self.callback(pairs)
            QMessageBox.information(self, "Success", "Output successfully analyzed")
        except Exception as e:
            self.log(f"Error analyzing:\n{str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to analyze output: {str(e)}")

    def _parse_pairdisplay(self, text: str) -> List[GADPair]:
        lines = [line.strip() for line in text.split('\n') 
              if line.strip() and not line.startswith('Group')]
        
        pairs = []
        for i in range(0, len(lines), 2):
            if i + 1 >= len(lines):
                break
                
            left_line = lines[i]
            right_line = lines[i + 1]
            
            try:
                match = re.match(r'(\w+)\s+([\w_]+)', left_line)
                group, name = match.groups()
                
                left_serial = re.search(r'(\d{6})', left_line).group(1)
                right_serial = re.search(r'(\d{6})', right_line).group(1)
                
                left_ldev = re.search(r'(\d+)\.(P|S)-VOL', left_line)
                right_ldev = re.search(r'(\d+)\.(P|S)-VOL', right_line)
                
                left_status = next(s for s in left_line.split() if s in ['PAIR', 'PSUS', 'SSUS', 'SSWS', 'PSUE', 'COPY'])
                right_status = next(s for s in right_line.split() if s in ['PAIR', 'PSUS', 'SSUS', 'SSWS', 'PSUE', 'COPY'])
                
                left_rw = re.search(r'([BL]/[BLM])', left_line).group(1)
                right_rw = re.search(r'([BL]/[BLM])', right_line).group(1)

                left_storage = StorageSystem(
                    serial_number=left_serial,
                    host=self._extract_port_info(left_line) or '',
                    ldev_number=left_ldev.group(1),
                    status=left_status, 
                    role=f"{left_ldev.group(2)}-VOL",
                    rw_status=left_rw,
                    instance='-IH10'
                )

                right_storage = StorageSystem(
                    serial_number=right_serial,
                    host=self._extract_port_info(right_line) or '',
                    ldev_number=right_ldev.group(1),
                    status=right_status,
                    role=f"{right_ldev.group(2)}-VOL",
                    rw_status=right_rw,
                    instance='-IH20'
                )

                pairs.append(GADPair(group=group, name=name,
                         left_storage=left_storage, right_storage=right_storage))
                
            except Exception as e:
                raise ValueError(f"Parsing error: {str(e)}\nLeft: {left_line}\nRight: {right_line}")

        return pairs

    def _extract_port_info(self, line: str) -> str:
        start = line.find('(CL')
        if start == -1:
            self.log("CL port start mark not found")
            return None
        end = line.find(')', start)
        if end == -1:
            self.log("Port end mark not found")
            return None
        port_info = line[start:end+1]
        self.log(f"Extracted port info: {port_info}")
        return port_info

class CommandOutput(QWidget):
    """Komandų išvesties komponentas"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Command Output")
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        self.output_field = QTextEdit()
        self.output_field.setReadOnly(True)
        self.output_field.setMaximumHeight(80)
        self.output_field.setStyleSheet("background-color: #f7f9fc;")
        layout.addWidget(self.output_field)

    def set_command(self, command: str):
        """Nustato komandos tekstą"""
        self.output_field.setText(command)

    def clear(self):
        """Išvalo komandos tekstą"""
        self.output_field.clear()

class HelpDialog(QDialog):
    """Pagalbos dialogo langas"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GAD Manager Help")
        self.setMinimumWidth(600)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #1a1f36;
            }
            QPushButton {
                background-color: #f7f9fc;
                border: 1px solid #d0d5dd;
                border-radius: 4px;
                color: #344054;
                padding: 6px 12px;
                font-weight: 500;
                min-width: 80px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Sukuriame Tab widget pagalbos skyriams
        tabs = QTabWidget()
        
        # Bendros informacijos tab
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        general_text = """
        <h3>GAD Manager Overview</h3>
        <p>GAD Manager is a tool for managing Global Active Device (GAD) pairs in Hitachi VSP storage systems. 
        It provides an intuitive interface for:</p>
        <ul>
            <li>Monitoring GAD pair status</li>
            <li>Managing pair operations (split, swap, resync)</li>
            <li>Generating HORCM configuration files</li>
        </ul>
        
        <h3>Main Features</h3>
        <ul>
            <li>Real-time status monitoring of GAD pairs</li>
            <li>Visual representation of storage system states</li>
            <li>One-click operations for common GAD tasks</li>
            <li>Automated HORCM configuration generation</li>
        </ul>
        """
        
        general_info = QLabel(general_text)
        general_info.setWordWrap(True)
        general_info.setTextFormat(Qt.RichText)
        general_layout.addWidget(general_info)
        general_layout.addStretch()
        
        # Operations tab
        operations_tab = QWidget()
        operations_layout = QVBoxLayout(operations_tab)
        
        operations_text = """
        <h3>Available Operations</h3>
        
        <h4>Split Operations</h4>
        <p><b>Split VSP1:</b> Suspends the pair from the primary storage system</p>
        <p><b>Split VSP2:</b> Suspends the pair from the secondary storage system</p>
        
        <h4>Swap Operations</h4>
        <p><b>Swap P→S:</b> Swaps the P-VOL to S-VOL role</p>
        <p><b>Swap S→P:</b> Swaps the S-VOL to P-VOL role</p>
        
        <h4>Resync Operation</h4>
        <p><b>Resync:</b> Resynchronizes a suspended pair</p>
        
        <h3>Status Indicators</h3>
        <p><b>PAIR:</b> Volumes are synchronized</p>
        <p><b>PSUS:</b> Pair suspended from primary side</p>
        <p><b>SSUS:</b> Pair suspended from secondary side</p>
        <p><b>SSWS:</b> Secondary side suspended with write access</p>
        <p><b>PSUE:</b> Pair suspended due to error</p>
        <p><b>COPY:</b> Initial copy in progress</p>
        """
        
        operations_info = QLabel(operations_text)
        operations_info.setWordWrap(True)
        operations_info.setTextFormat(Qt.RichText)
        operations_layout.addWidget(operations_info)
        operations_layout.addStretch()
        
        # HORCM tab
        horcm_tab = QWidget()
        horcm_layout = QVBoxLayout(horcm_tab)
        
        horcm_text = """
        <h3>HORCM Configuration</h3>
        <p>The HORCM Generator helps you create configuration files for both primary and secondary instances:</p>
        
        <h4>Required Information</h4>
        <ul>
            <li>HORCM server IP address</li>
            <li>VSP serial numbers</li>
            <li>VSP IP addresses</li>
            <li>Device group information</li>
            <li>LDEV numbers</li>
        </ul>
        
        <h4>Generated Files</h4>
        <p>The tool generates two configuration files:</p>
        <ul>
            <li><b>horcm10.conf:</b> Primary instance configuration</li>
            <li><b>horcm20.conf:</b> Secondary instance configuration</li>
        </ul>
        
        <h4>Shortcuts</h4>
        <ul>
            <li><b>Ctrl+S:</b> Save configuration files</li>
            <li><b>Ctrl+P:</b> Preview configurations</li>
        </ul>
        """
        
        horcm_info = QLabel(horcm_text)
        horcm_info.setWordWrap(True)
        horcm_info.setTextFormat(Qt.RichText)
        horcm_layout.addWidget(horcm_info)
        horcm_layout.addStretch()
        
        # Pridedame tabs
        tabs.addTab(general_tab, "General")
        tabs.addTab(operations_tab, "Operations")
        tabs.addTab(horcm_tab, "HORCM Config")
        
        layout.addWidget(tabs)
        
        # Mygtukai
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

class AboutDialog(QDialog):
    """About dialogo langas"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About GAD Manager")
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #1a1f36;
            }
            QPushButton {
                background-color: #f7f9fc;
                border: 1px solid #d0d5dd;
                border-radius: 4px;
                color: #344054;
                padding: 6px 12px;
                font-weight: 500;
                min-width: 80px;
            }
            QLabel[cssClass="link"] {
                color: #0052cc;
                text-decoration: underline;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Logo su pataisytu keliu
        logo_label = QLabel()
        try:
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
                
            icon_path = os.path.join(base_path, "icon.svg")
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                # Sukuriame pixmap su nurodytu dydžiu
                pixmap = icon.pixmap(QSize(128, 128))
                logo_label.setPixmap(pixmap)
                print(f"About logo įkeltas iš: {icon_path}")
            else:
                print(f"Įspėjimas: About logo failas nerastas {icon_path}")
        except Exception as e:
            print(f"Klaida įkeliant about logo: {e}")
        
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)
        
        # Title
        title = QLabel("GAD Manager")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #0052cc;
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Versijos informacija
        version_info = QLabel(f"""
            <p style='text-align: center;'>
            Version {APP_VERSION}<br>
            Release Date: {APP_RELEASE_DATE}<br>
            </p>
        """)
        version_info.setTextFormat(Qt.RichText)
        version_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_info)
        
        # Aprašymas
        description = QLabel("""
            <p style='text-align: center;'>
            GAD Manager is a professional tool for managing<br>
            Global Active Device pairs in VSP storage systems.<br>
            The tool provides an intuitive interface for GAD pair<br>
            management and HORCM configuration file generation.<br><br>
            © 2024 Aurimas. Licensed under GNU GPL v3.<br>
            <a href='https://www.gnu.org/licenses/gpl-3.0.html'>View license</a>
            </p>
        """)
        description.setTextFormat(Qt.RichText)
        description.setAlignment(Qt.AlignCenter)
        description.setOpenExternalLinks(True)
        layout.addWidget(description)
        
        # Kontaktinė informacija
        contact_info = QLabel("""
            <p style='text-align: center; color: #666;'>
            <b>Developer:</b><br>
            Aurimas<br>
            <a href='mailto:aurimasles@gmail.com'>aurimasles@gmail.com</a><br><br>
            <a href='https://www.paypal.com/donate/?hosted_button_id=FNVADCF5J5QKL'>Support this project - Donate via PayPal</a>
            </p>
        """)
        contact_info.setTextFormat(Qt.RichText)
        contact_info.setAlignment(Qt.AlignCenter)
        contact_info.setOpenExternalLinks(True)
        layout.addWidget(contact_info)
        
        layout.addStretch()
        
        # OK mygtukas
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

class ServerParametersGroup(QGroupBox):
    """HORCM serverio parametrų grupė"""
    def __init__(self, parent=None):
        super().__init__("HORCM Server Parameters", parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        layout.setSpacing(8)
        
        self.ip_entry = QLineEdit()
        self.ip_entry.setPlaceholderText("127.0.0.1")
        layout.addRow("HORCM Server IP:", self.ip_entry)
        
        info_label = QLabel("(This IP will be used for HORCM service)")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addRow("", info_label)
        
        self.setLayout(layout)
        
    def is_empty(self) -> bool:
        """Patikrina ar laukas tuščias"""
        return not self.ip_entry.text()
        
    def get_ip(self) -> str:
        """Grąžina įvestą IP arba placeholder reikšmę"""
        return self.ip_entry.text() or self.ip_entry.placeholderText()

class VSPParametersGroup(QGroupBox):
    """VSP parametrų grupė"""
    def __init__(self, vsp_num, parent=None):
        super().__init__(f"VSP{vsp_num} Parameters", parent)
        self.vsp_num = vsp_num
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        layout.setSpacing(8)
        
        self.serial_entry = QLineEdit()
        self.ip_entry = QLineEdit()
        
        self.serial_entry.setPlaceholderText(f"8{self.vsp_num*11111}")
        self.ip_entry.setPlaceholderText(f"{self.vsp_num}.{self.vsp_num}.{self.vsp_num}.{self.vsp_num}")
        
        layout.addRow("Serial Number:", self.serial_entry)
        layout.addRow("IP Address:", self.ip_entry)
        
        self.setLayout(layout)
        
    def is_empty(self) -> bool:
        """Patikrina ar visi laukai tušti"""
        return not self.serial_entry.text() and not self.ip_entry.text()
        
    def get_values(self) -> dict:
        """Grąžina įvestas reikšmes arba placeholder reikšmes"""
        if self.is_empty():
            return {
                'serial': self.serial_entry.placeholderText(),
                'ip': self.ip_entry.placeholderText()
            }
        return {
            'serial': self.serial_entry.text(),
            'ip': self.ip_entry.text()
        }

class LUNEntry(QFrame):
    """Vieno LUN įrašo komponentas"""
    removed = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        self.setStyleSheet("QFrame { background: #f7f9fc; border-radius: 4px; padding: 8px; }")
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        self.fields = {
            "group": QLineEdit(),
            "name": QLineEdit(),
            "ldev": QLineEdit()
        }
        
        self.fields["group"].setPlaceholderText("ORACLE")
        self.fields["name"].setPlaceholderText("GAD_TEST_DB")
        self.fields["ldev"].setPlaceholderText("52735")
        
        fields_layout = QGridLayout()
        fields_layout.setSpacing(4)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        
        for col, (key, value) in enumerate(self.fields.items()):
            fields_layout.addWidget(QLabel(f"{key.title()}:"), 0, col*2)
            fields_layout.addWidget(value, 0, col*2+1)
            if key == "group":
                value.setFixedWidth(60)
            elif key == "name":
                value.setFixedWidth(100)
            elif key == "ldev":
                value.setFixedWidth(60)
                
        layout.addLayout(fields_layout)
        
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: #f0f0f0;
                border: none;
                border-radius: 10px;
                color: #666;
                font-weight: bold;
                padding: 0;
                margin: 0;
            }
            QPushButton:hover {
                background: #e0e0e0;
                color: #333;
            }
        """)
        remove_btn.clicked.connect(self.remove_self)
        layout.addWidget(remove_btn)
        
        self.setLayout(layout)
    
    def has_any_input(self) -> bool:
        """Patikrina ar bent vienas laukas yra užpildytas"""
        return any(field.text() for field in self.fields.values())
        
    def is_empty(self) -> bool:
        """Patikrina ar visi laukai tušti"""
        return all(not field.text() for field in self.fields.values())
    
    def is_fully_filled(self) -> bool:
        """Patikrina ar visi laukai užpildyti"""
        return all(field.text() for field in self.fields.values())
        
    def get_values(self) -> dict:
        """Grąžina įvestas reikšmes arba placeholder reikšmes"""
        if self.is_empty():
            return {k: v.placeholderText() for k, v in self.fields.items()}
        elif not self.is_fully_filled():
            return None
        return {k: v.text() for k, v in self.fields.items()}
        
    def remove_self(self):
        """Pašalina šį LUN įrašą"""
        self.removed.emit(self)

class LUNConfigurationGroup(QGroupBox):
    """LUN konfigūracijos grupė"""
    def __init__(self, parent=None):
        super().__init__("LUN Configuration", parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        header_layout = QHBoxLayout()
        header_label = QLabel("Configured LUNs")
        header_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(header_label)
        
        add_btn = QPushButton("➕ Add LUN")
        add_btn.setMaximumWidth(100)
        add_btn.clicked.connect(self.add_lun)
        header_layout.addWidget(add_btn, alignment=Qt.AlignRight)
        
        layout.addLayout(header_layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMinimumHeight(300)
        
        scroll_widget = QWidget()
        self.lun_container = QVBoxLayout(scroll_widget)
        self.lun_container.setSpacing(8)
        self.lun_container.addStretch()
        scroll.setWidget(scroll_widget)
        
        layout.addWidget(scroll)
        self.setLayout(layout)
        
        self.add_lun()
        
    def add_lun(self):
        """Prideda naują LUN įrašą"""
        lun = LUNEntry()
        lun.removed.connect(self.remove_lun)
        self.lun_container.insertWidget(self.lun_container.count() - 1, lun)
        
    def remove_lun(self, lun):
        """Pašalina LUN įrašą"""
        if self.lun_container.count() > 2:  # >2 because of stretch
            lun.deleteLater()
        else:
            QMessageBox.warning(self, "Warning", "Cannot remove the last LUN entry!")
            
    def validate_luns(self) -> tuple[bool, str, list]:
        """Validuoja visus LUN įrašus"""
        lun_entries = []
        has_any_input = False
        
        for i in range(self.lun_container.count() - 1):
            widget = self.lun_container.itemAt(i).widget()
            if isinstance(widget, LUNEntry):
                lun_entries.append(widget)
                if widget.has_any_input():
                    has_any_input = True

        if not has_any_input:
            return True, "", [lun_entries[0].get_values()]
            
        valid_luns = []
        for lun in lun_entries:
            if not lun.is_empty() and not lun.is_fully_filled():
                return False, "Some LUN entries are partially filled. Please fill all fields or leave them empty.", []
            if lun.is_fully_filled():
                valid_luns.append(lun.get_values())

        if not valid_luns:
            return False, "No valid LUN entries found. Please fill all required fields.", []
            
        return True, "", valid_luns
            
    def get_lun_values(self) -> list:
        """Grąžina validžių LUN įrašų sąrašą"""
        is_valid, error_message, valid_luns = self.validate_luns()
        
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error_message)
            return []
            
        return valid_luns

class HORCMConfigGenerator:
    """HORCM konfigūracijos generavimo klasė"""
    def __init__(self):
        self.re = __import__('re')
    
    def validate_inputs(self, server_ip: str, vsp1: dict, vsp2: dict, luns: list) -> bool:
        """Validuoja įvesties duomenis"""
        # IP adresų validacija
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        for ip in [server_ip, vsp1['ip'], vsp2['ip']]:
            if not self.re.match(ip_pattern, ip):
                raise ValueError(f"Invalid IP address format: {ip}")

        # Serijos numerių validacija
        for serial in [vsp1['serial'], vsp2['serial']]:
            if not serial.isdigit() or len(serial) != 6:
                raise ValueError(f"Serial number must be 6 digits: {serial}")

        # LUN validacija
        if not luns:
            raise ValueError("At least one LUN configuration is required")

        for lun in luns:
            if not lun["group"]:
                raise ValueError("Group ID cannot be empty")
            if not lun["name"]:
                raise ValueError("Device name cannot be empty")
            if not lun["ldev"].isdigit():
                raise ValueError("LDEV number must be numeric")

        return True

    def generate_horcm10(self, server_ip: str, vsp1: dict, luns: list) -> str:
        """Generuoja HORCM10.conf turinį"""
        # LDEV sekcija
        ldev_lines = []
        for lun in luns:
            ldev_lines.append(f"{lun['group']}    {lun['name']}    "
                            f"{vsp1['serial']}    {lun['ldev']}    0")

        # INST sekcija
        unique_groups = {lun["group"] for lun in luns}
        inst_lines = []
        for group in sorted(unique_groups):
            inst_lines.append(f"{group}    {server_ip}    5020")

        return f"""HORCM_MON
# ip_address service poll(10ms) timeout(10ms)
{server_ip}    5010    1000       3000

HORCM_CMD
# VSP1 (Serial No.: {vsp1['serial']})
\\\\.\\CMD-{vsp1['serial']}-{luns[0]['ldev']}

HORCM_LDEV
# DeviceGroup, DeviceName, Serial#, CU:LDEV(LDEV#), MU#
{chr(10).join(ldev_lines)}

HORCM_INST
# DeviceGroup         ip_address      service
{chr(10).join(inst_lines)}"""

    def generate_horcm20(self, server_ip: str, vsp2: dict, luns: list) -> str:
        """Generuoja HORCM20.conf turinį"""
        # LDEV sekcija
        ldev_lines = []
        for lun in luns:
            ldev_lines.append(f"{lun['group']}    {lun['name']}    "
                            f"{vsp2['serial']}    {lun['ldev']}    0")

        # INST sekcija
        unique_groups = {lun["group"] for lun in luns}
        inst_lines = []
        for group in sorted(unique_groups):
            inst_lines.append(f"{group}    {server_ip}    5010")

        return f"""HORCM_MON
# ip_address service poll(10ms) timeout(10ms)
{server_ip}    5020    1000       3000

HORCM_CMD
# VSP2 (Serial No.: {vsp2['serial']})
\\\\.\\CMD-{vsp2['serial']}-{luns[0]['ldev']}

HORCM_LDEV
# DeviceGroup, DeviceName, Serial#, CU:LDEV(LDEV#), MU#
{chr(10).join(ldev_lines)}

HORCM_INST
# DeviceGroup         ip_address      service
{chr(10).join(inst_lines)}"""

class HORCMConfigFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.generator = HORCMConfigGenerator()
        self.init_ui()
    
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(16)

        # Kairė kolona
        left_column = QVBoxLayout()
        
        self.server_params = ServerParametersGroup()
        self.vsp1_params = VSPParametersGroup(1)
        self.vsp2_params = VSPParametersGroup(2)
        
        left_column.addWidget(self.server_params)
        left_column.addWidget(self.vsp1_params)
        left_column.addWidget(self.vsp2_params)

        # Mygtukai
        buttons_group = QGroupBox("Actions")
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        preview_btn = QPushButton("Generate Preview")
        preview_btn.setProperty("class", "primary")
        preview_btn.clicked.connect(self.update_preview)
        buttons_layout.addWidget(preview_btn)

        save_btn = QPushButton("Save Files")
        save_btn.clicked.connect(self.save_files)
        buttons_layout.addWidget(save_btn)

        buttons_group.setLayout(buttons_layout)
        left_column.addWidget(buttons_group)
        left_column.addStretch()

        # Vidurinė kolona
        self.lun_config = LUNConfigurationGroup()

        # Dešinė kolona - Preview
        right_column = QVBoxLayout()
        preview_group = QGroupBox("Configuration Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Consolas", 9))
        self.preview_text.setMinimumWidth(300)
        preview_layout.addWidget(self.preview_text)
        
        preview_group.setLayout(preview_layout)
        right_column.addWidget(preview_group)

        # Add columns to main layout
        main_layout.addLayout(left_column)
        main_layout.addWidget(self.lun_config)
        main_layout.addLayout(right_column)

        # Set column stretch factors
        main_layout.setStretch(0, 2)  # Left column
        main_layout.setStretch(1, 3)  # Middle column
        main_layout.setStretch(2, 2)  # Right column

    def all_fields_empty(self) -> bool:
        """Patikrina ar visi laukai tušti"""
        return (
            self.server_params.is_empty() and
            self.vsp1_params.is_empty() and
            self.vsp2_params.is_empty()
        )

    def validate_inputs(self) -> bool:
        """Validuoja įvesties laukus"""
        # Jei bent vienas laukas užpildytas, visi laukai turi būti užpildyti
        server_ip_filled = bool(self.server_params.ip_entry.text())
        vsp1_filled = bool(self.vsp1_params.serial_entry.text()) or bool(self.vsp1_params.ip_entry.text())
        vsp2_filled = bool(self.vsp2_params.serial_entry.text()) or bool(self.vsp2_params.ip_entry.text())
        
        any_field_filled = server_ip_filled or vsp1_filled or vsp2_filled
        
        if any_field_filled:
            if not server_ip_filled:
                QMessageBox.warning(self, "Validation Error", "HORCM server IP address is required!")
                return False
                
            if not (self.vsp1_params.serial_entry.text() and self.vsp1_params.ip_entry.text()):
                QMessageBox.warning(self, "Validation Error", "VSP1 serial number and IP address are required!")
                return False
                
            if not (self.vsp2_params.serial_entry.text() and self.vsp2_params.ip_entry.text()):
                QMessageBox.warning(self, "Validation Error", "VSP2 serial number and IP address are required!")
                return False
                
            # Tikriname LUN konfigūracijas (ši funkcija jau turi savo pranešimus)
            luns = self.lun_config.get_lun_values()
            if not luns:
                return False
        
        return True

    def collect_data(self) -> dict:
        """Surenka visus reikiamus duomenis iš UI"""
        use_placeholders = self.all_fields_empty()
        
        if use_placeholders:
            return {
                'server_ip': self.server_params.get_ip(),
                'vsp1': self.vsp1_params.get_values(),
                'vsp2': self.vsp2_params.get_values(),
                'luns': self.lun_config.get_lun_values()
            }
        else:
            return {
                'server_ip': self.server_params.ip_entry.text(),
                'vsp1': {
                    'serial': self.vsp1_params.serial_entry.text(),
                    'ip': self.vsp1_params.ip_entry.text()
                },
                'vsp2': {
                    'serial': self.vsp2_params.serial_entry.text(),
                    'ip': self.vsp2_params.ip_entry.text()
                },
                'luns': self.lun_config.get_lun_values()
            }

    def update_preview(self):
        """Atnaujina konfigūracijos peržiūrą"""
        try:
            if not self.validate_inputs():
                return
                
            data = self.collect_data()
            
            # Validuojame surinktus duomenis
            self.generator.validate_inputs(
                server_ip=data['server_ip'],
                vsp1=data['vsp1'],
                vsp2=data['vsp2'],
                luns=data['luns']
            )
            
            # Generuojame peržiūrą
            preview = "=== HORCM10.conf ===\n"
            preview += self.generator.generate_horcm10(
                server_ip=data['server_ip'],
                vsp1=data['vsp1'],
                luns=data['luns']
            )
            preview += "\n\n=== HORCM20.conf ===\n"
            preview += self.generator.generate_horcm20(
                server_ip=data['server_ip'],
                vsp2=data['vsp2'],
                luns=data['luns']
            )
            
            self.preview_text.setPlainText(preview)
            
        except Exception as e:
            QMessageBox.critical(self, "Klaida", str(e))

    def save_files(self):
        """Išsaugo konfigūracijos failus"""
        try:
            if not self.validate_inputs():
                return

            data = self.collect_data()
            
            # Validuojame
            self.generator.validate_inputs(
                server_ip=data['server_ip'],
                vsp1=data['vsp1'],
                vsp2=data['vsp2'],
                luns=data['luns']
            )
            
            # Pasirenkame išsaugojimo direktoriją
            save_dir = QFileDialog.getExistingDirectory(
                self,
                "Select Directory to Save Configuration Files",
                "",
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            
            if save_dir:
                # Išsaugome failus
                with open(f"{save_dir}/horcm10.conf", 'w') as f:
                    f.write(self.generator.generate_horcm10(
                        server_ip=data['server_ip'],
                        vsp1=data['vsp1'],
                        luns=data['luns']
                    ))
                    
                with open(f"{save_dir}/horcm20.conf", 'w') as f:
                    f.write(self.generator.generate_horcm20(
                        server_ip=data['server_ip'],
                        vsp2=data['vsp2'],
                        luns=data['luns']
                    ))
                    
                QMessageBox.information(
                    self,
                    "Success",
                    f"Configuration files saved successfully to:\n{save_dir}"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def keyPressEvent(self, event):
        """Apdoroja klavišų paspaudimus"""
        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_S:
                self.save_files()
            elif event.key() == Qt.Key_P:
                self.update_preview()
        else:
            super().keyPressEvent(event)

class MainWindow(QMainWindow):
    def show_help(self):
        """Rodo pagalbos dialogą"""
        help_dialog = HelpDialog(self)
        help_dialog.exec_()

    def show_about(self):
        """Rodo about dialogą"""
        about_dialog = AboutDialog(self)
        about_dialog.exec_()

    def __init__(self):
        super().__init__()
        self.init_update_controller()
        self.init_gad_controller()
        self.init_ui()

    def init_update_controller(self):
        """Inicializuoja atnaujinimų valdiklį"""
        self.update_controller = UpdateController(self)

    def init_gad_controller(self):
        """Inicializuoja GAD porų valdiklį"""
        self.gad_controller = GADController()

    def init_ui(self):
        self.setWindowTitle(f"GAD Manager {APP_VERSION}")
        self.setMinimumSize(1400, 750)
        self.setStyleSheet(ProStyle.STYLE)

        # Nustatome programos ikoną
        try:
            # PyInstaller sukuria temp katalogą ir saugo kelią _MEIPASS
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
                
            icon_path = os.path.join(base_path, "icon.svg")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                print(f"Ikona įkelta iš: {icon_path}")
            else:
                print(f"Įspėjimas: Ikonos failas nerastas {icon_path}")
        except Exception as e:
            print(f"Klaida nustatant ikoną: {e}")

        # Sukuriame meniu juostą
        menubar = self.menuBar()

        # Help meniu
        help_menu = menubar.addMenu('Update / Help')
        
        # Check for Updates action
        check_updates_action = help_menu.addAction('Check for Updates')
        check_updates_action.triggered.connect(self.check_for_updates)
        
        # Help veiksmą
        help_action = QAction('Help Contents', self)
        help_action.setShortcut('F1')
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        # About veiksmą
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Main layout
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(0)

        # Tab widget
        self.tab_widget = QTabWidget()

        # GAD Pairs tab
        self.pairs_tab = QWidget()
        pairs_layout = QVBoxLayout(self.pairs_tab)
        pairs_layout.setSpacing(0)
        pairs_layout.setContentsMargins(4, 4, 4, 4)

        # Sukuriame konteinerį viršutinei daliai
        top_container = QWidget()
        top_container.setContentsMargins(0, 0, 0, 0)
        top_layout = QVBoxLayout(top_container)
        top_layout.setSpacing(0)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Inicializuojame komponentus
        self.parser = OutputParserFrame(callback=self.update_from_parser)
        self.cmd_output = CommandOutput()

        # Įdedame į konteinerį
        top_layout.addWidget(self.parser)
        top_layout.addWidget(self.cmd_output)

        # Įdedame konteinerį į pagrindinį išdėstymą
        pairs_layout.addWidget(top_container)

        # Sukuriame scroll area GAD poroms
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Scroll widget su container
        scroll_widget = QWidget()
        self.pairs_container = QVBoxLayout(scroll_widget)
        self.pairs_container.setSpacing(4)
        self.pairs_container.setContentsMargins(8, 8, 8, 8)
        
        scroll_area.setWidget(scroll_widget)
        pairs_layout.addWidget(scroll_area)

        # HORCM tab
        self.horcm_tab = QWidget()
        horcm_layout = QVBoxLayout(self.horcm_tab)
        self.horcm_generator = HORCMConfigFrame()
        horcm_layout.addWidget(self.horcm_generator)

        # Add tabs
        self.tab_widget.addTab(self.pairs_tab, "GAD Pairs")
        self.tab_widget.addTab(self.horcm_tab, "HORCM Generator")

        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)

        # Status bar
        self.statusBar().showMessage("Ready")

    def update_from_parser(self, new_pairs: List[GADPair]):
        """Atnaujina porų informaciją iš parserio"""
        self.gad_controller.update_pairs(new_pairs)
        self.refresh_pairs_display()

    def refresh_pairs_display(self):
        """Atnaujina porų atvaizdavimą"""
        # Išvalo senus widgets
        while self.pairs_container.count():
            child = self.pairs_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Prideda naujas poras
        for pair in self.gad_controller.pairs:
            pair_panel = GadPairPanel(pair)
            self.pairs_container.addWidget(pair_panel)

            # Prijungia mygtukų signalus
            for btn_id, btn in pair_panel.buttons.items():
                btn.clicked.connect(lambda checked, p=pair, cmd=btn_id:
                                    self.handle_command(p, cmd))

    def handle_command(self, pair: GADPair, command: str):
        """Apdoroja mygtukų paspaudimus"""
        cmd_text = self.gad_controller.get_command_for_operation(pair, command)
        self.cmd_output.set_command(cmd_text)

    def check_for_updates(self):
        """Checks for and performs update if available"""
        self.statusBar().showMessage("Checking for updates...")
        if not self.update_controller.check_for_updates():
            self.statusBar().showMessage("No updates available")
        else:
            self.statusBar().showMessage("Update completed - please restart")

def main():
    app = QApplication(sys.argv)

    # Nustatome globalų šriftą
    app.setFont(QFont("Segoe UI", 9))

    # Nustatome spalvų paletę
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#f0f2f5"))
    palette.setColor(QPalette.WindowText, QColor("#1a1f36"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()