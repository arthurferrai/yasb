import datetime
import logging

import webbrowser
import os
import shutil
import sys
from pathlib import Path
import subprocess

import winshell
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon, QGuiApplication
from PyQt6.QtCore import QCoreApplication, QSize, Qt
from core.bar_manager import BarManager
from settings import GITHUB_URL, SCRIPT_PATH, APP_NAME, APP_NAME_FULL, DEFAULT_CONFIG_DIRECTORY, GITHUB_THEME_URL, BUILD_VERSION
from core.config import get_config
from core.console import WindowShellDialog

OS_STARTUP_FOLDER = os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs\Startup')
VBS_PATH = os.path.join(SCRIPT_PATH, 'yasb.vbs')

# Check if exe file exists
INSTALLATION_PATH = os.path.abspath(os.path.join(__file__, "../../.."))
EXE_PATH = os.path.join(INSTALLATION_PATH, 'yasb.exe')
SHORTCUT_FILENAME = "yasb.lnk"
AUTOSTART_FILE = EXE_PATH if os.path.exists(EXE_PATH) else VBS_PATH
WORKING_DIRECTORY = INSTALLATION_PATH if os.path.exists(EXE_PATH) else SCRIPT_PATH
 
class MenuExt(QMenu):
    def focusOutEvent(self, event):
        self.close()
        super().focusOutEvent(event)   
        
class TrayIcon(QSystemTrayIcon):
    def __init__(self, bar_manager: BarManager):
        super().__init__()
        self._bar_manager = bar_manager
        self._docs_url = GITHUB_URL
        self._icon = QIcon()
        self._load_favicon()
        self._load_context_menu()
        self.setToolTip(f"{APP_NAME}")
        self._load_config()
 
        
    def _load_config(self):
        try:
            config = get_config(show_error_dialog=True)
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return
        if config['komorebi']:
            self.komorebi_start = config['komorebi']["start_command"]
            self.komorebi_stop = config['komorebi']["stop_command"]
            self.komorebi_reload = config['komorebi']["reload_command"]
            
    def _load_favicon(self):
        # Get the current directory of the script
        parent_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._icon.addFile(os.path.join(parent_directory, 'assets', 'images', 'app_icon.png'), QSize(48, 48))
        self.setIcon(self._icon)
        
 
        
    def _load_context_menu(self):
        menu = MenuExt()
        menu.setWindowModality(Qt.WindowModality.WindowModal)
        style_sheet = """
        QMenu {
            background-color: #26292b;
            color: #ffffff;
            border:1px solid #373b3e;
            padding:5px 0;
            margin:0;
            border-radius:6px
        }
        QMenu::item {
            margin:0 4px;
            padding: 4px 12px 5px 12px;
            border-radius:4px;
            font-size: 11px;
            font-weight: 600;
            font-family: 'Segoe UI', sans-serif;
        }
        QMenu::item:selected {
            background-color: #373b3e;
        }
        QMenu::separator {
            height: 1px;
            background: #373b3e;
            margin:5px 0;
        }
        QMenu::right-arrow {
            width: 8px;
            height: 8px;
            padding-right:24px;
        }
        """
        menu.setStyleSheet(style_sheet)
        
        github_action = menu.addAction("Visit GitHub")
        github_action.triggered.connect(self._open_docs_in_browser)
        
        open_config_action = menu.addAction("Open Config")
        open_config_action.triggered.connect(self._open_config)
        
        reload_action = menu.addAction("Reload YASB")
        reload_action.triggered.connect(self._reload_application)
        
        menu.addSeparator()
        debug_menu = menu.addMenu("Debug")
        info_action = debug_menu.addAction("Information")
        info_action.triggered.connect(self._show_info)
        
        if self.is_komorebi_installed():
            komorebi_menu = menu.addMenu("Komorebi")
            start_komorebi = komorebi_menu.addAction("Start Komorebi")
            start_komorebi.triggered.connect(self._start_komorebi)
            
            stop_komorebi = komorebi_menu.addAction("Stop Komorebi")
            stop_komorebi.triggered.connect(self._stop_komorebi)
            
            reload_komorebi = komorebi_menu.addAction("Reload Komorebi")
            reload_komorebi.triggered.connect(self._reload_komorebi)
            
            menu.addSeparator()

        if self.is_autostart_enabled():
            disable_startup_action = menu.addAction("Disable Autostart")
            disable_startup_action.triggered.connect(self._disable_startup)
        else:
            enable_startup_action = menu.addAction("Enable Autostart")
            enable_startup_action.triggered.connect(self._enable_startup)
      
        logs_action = debug_menu.addAction("Logs")
        logs_action.triggered.connect(self._open_logs)

        about_action = menu.addAction("About")
        about_action.triggered.connect(self._show_about_dialog)
        
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self._exit_application)
        
        self.setContextMenu(menu)

    def is_autostart_enabled(self):
        return os.path.exists(os.path.join(OS_STARTUP_FOLDER, SHORTCUT_FILENAME))

    def is_komorebi_installed(self):
        try:
            komorebi_path = shutil.which('komorebi')
            return komorebi_path is not None
        except Exception as e:
            logging.error(f"Error checking komorebi installation: {e}")
            return False

    def _enable_startup(self):
        shortcut_path = os.path.join(OS_STARTUP_FOLDER, SHORTCUT_FILENAME)
        try:
            with winshell.shortcut(shortcut_path) as shortcut:
                shortcut.path = AUTOSTART_FILE
                shortcut.working_directory = WORKING_DIRECTORY
                shortcut.description = "Shortcut to yasb.vbs"
            logging.info(f"Created shortcut at {shortcut_path}")
        except Exception as e:
            logging.error(f"Failed to create startup shortcut: {e}")
        self._load_context_menu()  # Reload context menu

    def _disable_startup(self):
        shortcut_path = os.path.join(OS_STARTUP_FOLDER, SHORTCUT_FILENAME)
        if os.path.exists(shortcut_path):
            try:
                os.remove(shortcut_path)
                logging.info(f"Removed shortcut from {shortcut_path}")
            except Exception as e:
                logging.error(f"Failed to remove startup shortcut: {e}")
        self._load_context_menu()  # Reload context menu

    def _open_config(self):
        CONFIG_DIR = os.path.join(Path.home(), DEFAULT_CONFIG_DIRECTORY)
        try:
            subprocess.run(["explorer", str(CONFIG_DIR)])
        except Exception as e:
            logging.error(f"Failed to open config directory: {e}")

    def _start_komorebi(self):
        try:
            subprocess.run(self.komorebi_start, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True)
        except Exception as e:
            logging.error(f"Failed to start komorebi: {e}")

    def _stop_komorebi(self):
        try:
            subprocess.run(self.komorebi_stop, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True)
        except Exception as e:
            logging.error(f"Failed to stop komorebi: {e}")

    def _reload_komorebi(self):
        try:
            subprocess.run(self.komorebi_reload, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True)
        except Exception as e:
            logging.error(f"Failed to reload komorebi: {e}")

    def _reload_application(self):
        logging.info("Reloading Application...")
        os.execl(sys.executable, sys.executable, *sys.argv)

    def _exit_application(self):
        logging.info("Exiting Application from tray...")
        QCoreApplication.exit(0)

    def _open_docs_in_browser(self):
        webbrowser.open(self._docs_url)

    def _show_about_dialog(self):
        about_text = f"""
        <div style="font-family:'Segoe UI',sans-serif;">
        <div style="font-size:20px;font-weight:700;">{APP_NAME} REBORN</div><br/>
        <div style="font-size:14px;font-weight:500">{APP_NAME_FULL}</div>
        <div style="font-size:12px;">Version: {BUILD_VERSION}</div><br>
        <div><a href="{GITHUB_URL}">{GITHUB_URL}</a></div>
        <div><a href="{GITHUB_THEME_URL}">{GITHUB_THEME_URL}</a></div>
        </div>
        """
        about_box = QMessageBox()
        about_box.setWindowTitle("About YASB")
        
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'images', 'app_icon.png')
        icon = QIcon(icon_path)
        about_box.setIconPixmap(icon.pixmap(48, 48))
        about_box.setWindowIcon(icon)
        about_box.setText(about_text)
        about_box.exec()

    def _show_info(self):
        import platform
        import socket
        import uuid
        import psutil
        screens = QGuiApplication.screens()
        # monitor information
        screens_info = """
        <div style="font-size:16px;font-weight:bold;margin-bottom:8px">Monitor Information</div>
        <div style="font-size:12px">
        """
        for screen in screens:
            geometry = screen.geometry()
            available_geometry = screen.availableGeometry()
            physical_size = screen.physicalSize()
            is_primary = " (Primary)" if screen == QGuiApplication.primaryScreen() else ""
            device_pixel_ratio = screen.devicePixelRatio()
            
            screens_info += f"<div>Monitor: {screen.name()}{is_primary}</div>"
            screens_info += f"<div> - Geometry: x={geometry.x()}, y={geometry.y()}, width={geometry.width() * device_pixel_ratio}, height={geometry.height() * device_pixel_ratio}</div>"
            screens_info += f"<div> - Available Geometry: x={available_geometry.x()}, y={available_geometry.y()}, width={available_geometry.width() * device_pixel_ratio}, height={available_geometry.height() * device_pixel_ratio}</div>"
            screens_info += f"<div> - Physical Size: width={physical_size.width()}mm, height={physical_size.height()}mm</div>"
            screens_info += f"<div> - Logical DPI: {screen.logicalDotsPerInch()}</div>"
            screens_info += f"<div> - Physical DPI: {screen.physicalDotsPerInch()}</div><br>"
        screens_info += "</div>"

        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)

        mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)][::-1])
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot_time

        system_info = """
        <div style="font-size:16px;font-weight:bold;margin-bottom:8px">System Information</div>
        <div style="font-size:12px">
        System: {system}<br>
        Release: {release}<br>
        Version: {version}<br>
        Hostname: {hostname}<br>
        Machine: {machine}<br>
        Processor: {processor}<br>
        Uptime: {uptime}<br>
        IP Address: {ip_address}<br>
        MAC Address: {mac_address}<br>
        </div>
        """.format(
            system=platform.system(),
            release=platform.release(),
            version=platform.version(),
            hostname=hostname,
            machine=platform.machine(),
            processor=platform.processor(),
            uptime=str(uptime).split('.')[0],
            ip_address=ip_address,
            mac_address=mac_address
        )
        
        # Combine both sections
        screens_info += system_info
        
        # Create a QMessageBox instance
        info_box = QMessageBox()
        info_box.setWindowTitle("System Information")
        info_box.setTextFormat(Qt.TextFormat.RichText)
        info_box.setText(screens_info)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'images', 'app_icon.png')
        icon = QIcon(icon_path)
 
        info_box.setWindowIcon(icon)
        info_box.exec()
        
    def _open_logs(self):
        WindowShellDialog().exec()