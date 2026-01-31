#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ScreenOCR - Desktop Screenshot OCR Tool
Program Entry Point
"""

import sys
import os

# Get script directory for log file
_script_dir = os.path.dirname(os.path.abspath(__file__))
_log_path = os.path.join(os.path.dirname(_script_dir), 'startup_error.log')

# Global error handler - capture all errors to log file
def _setup_error_logging():
    """Setup error logging for pythonw.exe environment."""
    if sys.stdout is None or sys.stderr is None:
        try:
            log_file = open(_log_path, 'w', encoding='utf-8')
            if sys.stdout is None:
                sys.stdout = log_file
            if sys.stderr is None:
                sys.stderr = log_file
        except:
            # Last resort - use devnull
            if sys.stdout is None:
                sys.stdout = open(os.devnull, 'w', encoding='utf-8')
            if sys.stderr is None:
                sys.stderr = open(os.devnull, 'w', encoding='utf-8')

_setup_error_logging()

import threading

# Ensure UTF-8 output (only when stdout has buffer attribute, skip if using devnull)
if sys.platform == 'win32':
    import codecs
    # Only wrap if stdout has buffer (not devnull file)
    if sys.stdout is not None and hasattr(sys.stdout, 'buffer') and sys.stdout.buffer is not None:
        try:
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        except Exception:
            pass  # Ignore errors, keep current stdout
    if sys.stderr is not None and hasattr(sys.stderr, 'buffer') and sys.stderr.buffer is not None:
        try:
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
        except Exception:
            pass  # Ignore errors, keep current stderr

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtNetwork import QLocalServer, QLocalSocket


# Single instance unique identifier
SINGLE_INSTANCE_KEY = "ScreenOCR_SingleInstance_Key_v1"


class SingleInstanceManager(QObject):
    """Manager for single instance application.

    Uses QLocalServer to ensure only one instance runs.
    When a second instance tries to start, it sends a message to the first instance
    to show and activate its window, then exits.
    """
    show_window_requested = Signal()

    def __init__(self):
        super().__init__()
        self._server = None
        self._is_primary = False

    def try_to_run(self) -> bool:
        """Try to become the primary instance.

        Returns:
            True if this is the primary instance and should continue running.
            False if another instance is already running (this instance should exit).
        """
        try:
            # Try to connect to existing instance
            socket = QLocalSocket()
            socket.connectToServer(SINGLE_INSTANCE_KEY)

            if socket.waitForConnected(500):
                # Another instance is running - send show message
                socket.write(b"SHOW")
                socket.waitForBytesWritten(1000)
                socket.disconnectFromServer()
                print("[INFO] Another instance is already running. Activating existing window.")
                return False

            # No existing instance - become the primary
            # First, always remove stale server (in case of crash or unclean exit)
            QLocalServer.removeServer(SINGLE_INSTANCE_KEY)

            self._server = QLocalServer()

            if not self._server.listen(SINGLE_INSTANCE_KEY):
                print(f"[WARNING] Failed to create single instance server: {self._server.errorString()}")
                # Try one more time after removing
                QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
                if not self._server.listen(SINGLE_INSTANCE_KEY):
                    print("[WARNING] Single instance check disabled, continuing anyway")
                    return True  # Continue anyway

            self._server.newConnection.connect(self._on_new_connection)
            self._is_primary = True
            print("[INFO] Single instance server started")
            return True
        except Exception as e:
            # If any error occurs, just continue running
            print(f"[WARNING] Single instance check failed: {e}, continuing anyway")
            return True

    def _on_new_connection(self):
        """Handle connection from another instance."""
        socket = self._server.nextPendingConnection()
        if socket:
            socket.waitForReadyRead(1000)
            data = socket.readAll().data()
            if data == b"SHOW":
                print("[INFO] Received show request from another instance")
                self.show_window_requested.emit()
            socket.disconnectFromServer()

    def cleanup(self):
        """Cleanup server on exit."""
        if self._server:
            self._server.close()
            self._server = None


class GlobalHotkeyManager(QObject):
    """Global hotkey manager using keyboard library."""
    hotkey_triggered = Signal()
    alt_hotkey_triggered = Signal()  # Alternative screenshot hotkey

    def __init__(self, hotkey='ctrl+shift+o', alt_hotkey='f5'):
        super().__init__()
        self.hotkey = hotkey
        self.alt_hotkey = alt_hotkey
        self._running = False
        self._enabled = True
        self._registered_hotkeys = []

    def start(self):
        """Start listening for global hotkey."""
        if not self._enabled:
            return

        try:
            import keyboard

            # Register main hotkey
            keyboard.add_hotkey(self.hotkey, self._on_hotkey)
            self._registered_hotkeys.append(self.hotkey)
            print(f"[INFO] Global hotkey registered: {self.hotkey.upper()}")

            # Register alternative hotkey if different
            if self.alt_hotkey and self.alt_hotkey != self.hotkey:
                keyboard.add_hotkey(self.alt_hotkey, self._on_alt_hotkey)
                self._registered_hotkeys.append(self.alt_hotkey)
                print(f"[INFO] Alternative hotkey registered: {self.alt_hotkey.upper()}")

            self._running = True
        except ImportError:
            print("[WARNING] keyboard library not installed. Global hotkey disabled.")
            print("[WARNING] Install with: pip install keyboard")
        except Exception as e:
            print(f"[WARNING] Failed to register global hotkey: {e}")

    def stop(self):
        """Stop listening for global hotkey."""
        if self._running:
            try:
                import keyboard
                for hotkey in self._registered_hotkeys:
                    try:
                        keyboard.remove_hotkey(hotkey)
                    except Exception:
                        pass
                self._registered_hotkeys.clear()
                self._running = False
            except Exception:
                pass

    def update_hotkeys(self, hotkey=None, alt_hotkey=None, enabled=None):
        """Update hotkey configuration."""
        changed = False

        if enabled is not None:
            self._enabled = enabled
            changed = True

        if hotkey is not None and hotkey != self.hotkey:
            self.hotkey = hotkey
            changed = True

        if alt_hotkey is not None and alt_hotkey != self.alt_hotkey:
            self.alt_hotkey = alt_hotkey
            changed = True

        if changed and self._running:
            # Restart with new hotkeys
            self.stop()
            if self._enabled:
                self.start()

    def set_enabled(self, enabled: bool):
        """Enable or disable hotkeys."""
        if enabled != self._enabled:
            self._enabled = enabled
            if self._running:
                self.stop()
            if enabled:
                self.start()

    def _on_hotkey(self):
        """Handle main hotkey press - emit signal to main thread."""
        if self._enabled:
            self.hotkey_triggered.emit()

    def _on_alt_hotkey(self):
        """Handle alternative hotkey press - emit signal to main thread."""
        if self._enabled:
            self.alt_hotkey_triggered.emit()


# Global reference to hotkey manager
_hotkey_manager = None


def create_tray_icon():
    """Create a simple tray icon programmatically."""
    # Create a 32x32 icon with "OCR" text
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 122, 204))  # Blue background

    painter = QPainter(pixmap)
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Segoe UI", 8, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "OCR")
    painter.end()

    return QIcon(pixmap)


class SystemTrayManager(QObject):
    """System tray icon manager."""
    screenshot_requested = Signal()
    show_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon = None

    def setup(self, app):
        """Setup system tray icon and menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("[WARNING] System tray is not available")
            return False

        # Create tray icon
        self.tray_icon = QSystemTrayIcon(create_tray_icon(), app)
        self.tray_icon.setToolTip("ScreenOCR - 按 Ctrl+Shift+O 截图")

        # Create context menu
        menu = QMenu()

        # Screenshot action
        screenshot_action = menu.addAction("截图 (Ctrl+Shift+O)")
        screenshot_action.triggered.connect(self.screenshot_requested.emit)

        # Show window action
        show_action = menu.addAction("显示窗口")
        show_action.triggered.connect(self.show_requested.emit)

        menu.addSeparator()

        # Quit action
        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(self.quit_requested.emit)

        self.tray_icon.setContextMenu(menu)

        # Double-click to show window
        self.tray_icon.activated.connect(self._on_activated)

        # Show tray icon
        self.tray_icon.show()
        print("[INFO] System tray icon created")
        return True

    def _on_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click - show window on Windows
            self.show_requested.emit()

    def show_message(self, title, message, icon=QSystemTrayIcon.MessageIcon.Information):
        """Show a tray notification message."""
        if self.tray_icon:
            self.tray_icon.showMessage(title, message, icon, 3000)

    def cleanup(self):
        """Cleanup tray icon."""
        if self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon = None


# Global reference to tray manager
_tray_manager = None


def create_splash_screen():
    """Create and show splash screen for faster perceived startup."""
    from PySide6.QtWidgets import QSplashScreen
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QFontMetrics

    # Create splash pixmap
    pixmap = QPixmap(400, 250)
    pixmap.fill(QColor("#1e1e1e"))

    painter = QPainter(pixmap)

    # Draw gradient background
    from PySide6.QtGui import QLinearGradient
    gradient = QLinearGradient(0, 0, 0, 250)
    gradient.setColorAt(0, QColor("#2d2d2d"))
    gradient.setColorAt(1, QColor("#1e1e1e"))
    painter.fillRect(pixmap.rect(), gradient)

    # Draw title
    painter.setPen(QColor("#ffffff"))
    title_font = QFont("Segoe UI", 24, QFont.Weight.Bold)
    painter.setFont(title_font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "\nScreenOCR")

    # Draw subtitle
    painter.setPen(QColor("#007acc"))
    subtitle_font = QFont("Segoe UI", 12)
    painter.setFont(subtitle_font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "\n\n\n\n桌面截图 OCR 工具")

    # Draw loading text
    painter.setPen(QColor("#a0a0a0"))
    loading_font = QFont("Segoe UI", 10)
    painter.setFont(loading_font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, "正在启动...\n")

    # Draw version
    painter.setPen(QColor("#6e6e6e"))
    version_font = QFont("Segoe UI", 9)
    painter.setFont(version_font)
    painter.drawText(pixmap.rect().adjusted(0, 0, -20, -10),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                    "v1.0.0")

    painter.end()

    splash = QSplashScreen(pixmap, Qt.WindowType.FramelessWindowHint)
    splash.show()
    return splash


def main():
    """Application entry point."""
    global _hotkey_manager, _tray_manager

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ScreenOCR")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Archie")

    # Single instance check - must be after QApplication is created
    single_instance = SingleInstanceManager()
    if not single_instance.try_to_run():
        # Another instance is running, exit
        sys.exit(0)

    # Prevent app from quitting when main window is closed (keep in tray)
    app.setQuitOnLastWindowClosed(False)

    # Show splash screen immediately for faster perceived startup
    splash = create_splash_screen()
    app.processEvents()  # Ensure splash is shown

    # Apply dark theme stylesheet
    app.setStyleSheet(get_dark_theme_stylesheet())

    # Import here to avoid circular import
    from main_window import MainWindow
    from settings import SettingsManager

    # Load settings
    settings_manager = SettingsManager()
    settings = settings_manager.settings

    window = MainWindow()

    # Connect single instance show request to window
    def show_and_activate():
        """Show and activate the main window."""
        window.showNormal()
        window.raise_()
        window.activateWindow()
        # On Windows, need extra steps to bring window to front
        if sys.platform == 'win32':
            try:
                import ctypes
                hwnd = int(window.winId())
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass

    single_instance.show_window_requested.connect(show_and_activate)

    # Setup system tray manager
    _tray_manager = SystemTrayManager()
    if _tray_manager.setup(app):
        _tray_manager.screenshot_requested.connect(window.start_screenshot)
        _tray_manager.show_requested.connect(show_and_activate)
        _tray_manager.quit_requested.connect(app.quit)

    # Setup global hotkey manager with settings
    hotkey = settings_manager.get('hotkey', 'ctrl+shift+o')
    alt_hotkey = settings_manager.get('hotkey_screenshot', 'f5')
    hotkey_enabled = settings_manager.get('hotkey_enabled', True)

    _hotkey_manager = GlobalHotkeyManager(hotkey, alt_hotkey)
    _hotkey_manager.set_enabled(hotkey_enabled)
    _hotkey_manager.hotkey_triggered.connect(window.start_screenshot)
    _hotkey_manager.alt_hotkey_triggered.connect(window.start_screenshot)
    _hotkey_manager.start()

    # Connect settings changed signal to update hotkeys
    def on_settings_changed():
        """Update hotkeys when settings change."""
        new_hotkey = settings_manager.get('hotkey', 'ctrl+shift+o')
        new_alt_hotkey = settings_manager.get('hotkey_screenshot', 'f5')
        new_enabled = settings_manager.get('hotkey_enabled', True)
        _hotkey_manager.update_hotkeys(
            hotkey=new_hotkey,
            alt_hotkey=new_alt_hotkey,
            enabled=new_enabled
        )

    window.settings_changed.connect(on_settings_changed)

    # Show main window and close splash
    window.show()
    splash.finish(window)

    # Cleanup on exit
    def cleanup():
        if _hotkey_manager:
            _hotkey_manager.stop()
        if _tray_manager:
            _tray_manager.cleanup()
        single_instance.cleanup()
        # Cleanup main window resources
        window.force_close()

    app.aboutToQuit.connect(cleanup)

    sys.exit(app.exec())


def get_dark_theme_stylesheet():
    """Return dark theme QSS stylesheet."""
    return """
    /* Main Window */
    QMainWindow {
        background-color: #1e1e1e;
    }

    /* Central Widget */
    QWidget {
        background-color: #1e1e1e;
        color: #d4d4d4;
        font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
        font-size: 13px;
    }

    /* Tool Bar */
    QToolBar {
        background-color: #2d2d2d;
        border: none;
        padding: 4px;
        spacing: 4px;
    }

    QToolBar::separator {
        background-color: #3e3e3e;
        width: 1px;
        margin: 4px 8px;
    }

    QToolButton {
        background-color: transparent;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        color: #d4d4d4;
    }

    QToolButton:hover {
        background-color: #3e3e3e;
    }

    QToolButton:pressed {
        background-color: #4e4e4e;
    }

    /* Status Bar */
    QStatusBar {
        background-color: #007acc;
        color: #ffffff;
        padding: 2px;
    }

    QStatusBar::item {
        border: none;
    }

    /* Splitter */
    QSplitter::handle {
        background-color: #3e3e3e;
    }

    QSplitter::handle:horizontal {
        width: 2px;
    }

    QSplitter::handle:vertical {
        height: 2px;
    }

    /* Text Edit */
    QTextEdit, QPlainTextEdit {
        background-color: #252526;
        color: #d4d4d4;
        border: 1px solid #3e3e3e;
        border-radius: 4px;
        padding: 8px;
        font-family: "Consolas", "Microsoft YaHei UI", monospace;
        font-size: 14px;
    }

    QTextEdit:focus, QPlainTextEdit:focus {
        border-color: #007acc;
    }

    /* Labels */
    QLabel {
        color: #d4d4d4;
        background-color: transparent;
    }

    /* Group Box */
    QGroupBox {
        border: 1px solid #3e3e3e;
        border-radius: 4px;
        margin-top: 12px;
        padding-top: 8px;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: #d4d4d4;
    }

    /* Push Button */
    QPushButton {
        background-color: #0e639c;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        min-width: 80px;
    }

    QPushButton:hover {
        background-color: #1177bb;
    }

    QPushButton:pressed {
        background-color: #0d5a8c;
    }

    QPushButton:disabled {
        background-color: #3e3e3e;
        color: #6e6e6e;
    }

    /* Scroll Bar */
    QScrollBar:vertical {
        background-color: #1e1e1e;
        width: 12px;
        margin: 0;
    }

    QScrollBar::handle:vertical {
        background-color: #5a5a5a;
        border-radius: 4px;
        min-height: 30px;
        margin: 2px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #6e6e6e;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }

    QScrollBar:horizontal {
        background-color: #1e1e1e;
        height: 12px;
        margin: 0;
    }

    QScrollBar::handle:horizontal {
        background-color: #5a5a5a;
        border-radius: 4px;
        min-width: 30px;
        margin: 2px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: #6e6e6e;
    }

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
    }

    /* Menu */
    QMenu {
        background-color: #2d2d2d;
        border: 1px solid #3e3e3e;
        padding: 4px;
    }

    QMenu::item {
        padding: 6px 24px;
        border-radius: 2px;
    }

    QMenu::item:selected {
        background-color: #094771;
    }

    QMenu::separator {
        height: 1px;
        background-color: #3e3e3e;
        margin: 4px 8px;
    }

    /* Combo Box */
    QComboBox {
        background-color: #3c3c3c;
        color: #d4d4d4;
        border: 1px solid #3e3e3e;
        border-radius: 4px;
        padding: 4px 8px;
        min-width: 120px;
    }

    QComboBox:hover {
        border-color: #007acc;
    }

    QComboBox::drop-down {
        border: none;
        width: 20px;
    }

    QComboBox QAbstractItemView {
        background-color: #2d2d2d;
        border: 1px solid #3e3e3e;
        selection-background-color: #094771;
    }
    """


if __name__ == "__main__":
    main()
