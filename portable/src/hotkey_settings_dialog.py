#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ScreenOCR - Hotkey Settings Dialog
Custom hotkey configuration with conflict detection.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialogButtonBox, QGroupBox, QGridLayout, QMessageBox,
    QLineEdit, QCheckBox, QWidget, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QKeyEvent


class HotkeyCaptureEdit(QLineEdit):
    """Custom line edit that captures keyboard input as hotkey."""

    hotkey_captured = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("点击此处并按快捷键...")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._capturing = False
        self._current_hotkey = ""

    def focusInEvent(self, event):
        """Start capturing when focused."""
        super().focusInEvent(event)
        self._capturing = True
        self.setPlaceholderText("请按下快捷键组合...")
        self.setStyleSheet("""
            QLineEdit {
                background-color: #094771;
                color: #ffffff;
                border: 2px solid #007acc;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
        """)

    def focusOutEvent(self, event):
        """Stop capturing when focus lost."""
        super().focusOutEvent(event)
        self._capturing = False
        self.setPlaceholderText("点击此处并按快捷键...")
        self.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #007acc;
            }
        """)

    def keyPressEvent(self, event: QKeyEvent):
        """Capture key press as hotkey."""
        if not self._capturing:
            super().keyPressEvent(event)
            return

        # Get modifiers
        modifiers = []
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            modifiers.append("ctrl")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            modifiers.append("alt")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append("shift")
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
            modifiers.append("win")

        # Get key
        key = event.key()

        # Ignore modifier-only presses
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift, Qt.Key.Key_Meta):
            return

        # Convert key to string
        key_map = {
            Qt.Key.Key_F1: "f1", Qt.Key.Key_F2: "f2", Qt.Key.Key_F3: "f3",
            Qt.Key.Key_F4: "f4", Qt.Key.Key_F5: "f5", Qt.Key.Key_F6: "f6",
            Qt.Key.Key_F7: "f7", Qt.Key.Key_F8: "f8", Qt.Key.Key_F9: "f9",
            Qt.Key.Key_F10: "f10", Qt.Key.Key_F11: "f11", Qt.Key.Key_F12: "f12",
            Qt.Key.Key_Escape: "esc", Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Space: "space", Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Enter: "enter", Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Delete: "delete", Qt.Key.Key_Insert: "insert",
            Qt.Key.Key_Home: "home", Qt.Key.Key_End: "end",
            Qt.Key.Key_PageUp: "pageup", Qt.Key.Key_PageDown: "pagedown",
            Qt.Key.Key_Up: "up", Qt.Key.Key_Down: "down",
            Qt.Key.Key_Left: "left", Qt.Key.Key_Right: "right",
            Qt.Key.Key_Print: "print", Qt.Key.Key_ScrollLock: "scrolllock",
            Qt.Key.Key_Pause: "pause", Qt.Key.Key_NumLock: "numlock",
            Qt.Key.Key_0: "0", Qt.Key.Key_1: "1", Qt.Key.Key_2: "2",
            Qt.Key.Key_3: "3", Qt.Key.Key_4: "4", Qt.Key.Key_5: "5",
            Qt.Key.Key_6: "6", Qt.Key.Key_7: "7", Qt.Key.Key_8: "8",
            Qt.Key.Key_9: "9",
        }

        if key in key_map:
            key_str = key_map[key]
        elif Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            key_str = chr(key).lower()
        elif Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            key_str = chr(key)
        else:
            # Try to get key from QKeySequence
            seq = QKeySequence(key)
            key_str = seq.toString().lower()
            if not key_str:
                return

        # Build hotkey string
        if modifiers:
            self._current_hotkey = "+".join(modifiers + [key_str])
        else:
            self._current_hotkey = key_str

        self.setText(self._current_hotkey.upper() if len(self._current_hotkey) <= 3 else self._current_hotkey)
        self.hotkey_captured.emit(self._current_hotkey)

        # Clear focus to stop capturing
        self.clearFocus()

    def get_hotkey(self) -> str:
        """Get the captured hotkey."""
        return self._current_hotkey

    def set_hotkey(self, hotkey: str):
        """Set the hotkey value."""
        self._current_hotkey = hotkey
        if hotkey:
            # Format for display
            parts = hotkey.split('+')
            display_parts = []
            for p in parts:
                p = p.strip()
                if len(p) <= 3 and not p.startswith('f'):
                    display_parts.append(p.upper())
                else:
                    display_parts.append(p.capitalize())
            self.setText('+'.join(display_parts))
        else:
            self.clear()


class HotkeySettingsDialog(QDialog):
    """Dialog for configuring custom hotkeys."""

    hotkeys_changed = Signal(dict)

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.hotkey_edits = {}
        self.original_hotkeys = {}

        self.setWindowTitle("快捷键设置")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("自定义快捷键")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel("点击输入框并按下想要的快捷键组合。功能键(F1-F12)可以单独使用。")
        desc_label.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Global enable checkbox
        self.enable_checkbox = QCheckBox("启用全局快捷键")
        self.enable_checkbox.setStyleSheet("""
            QCheckBox {
                color: #d4d4d4;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        layout.addWidget(self.enable_checkbox)

        # Scroll area for hotkey settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(12)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        # Hotkey group
        hotkey_group = QGroupBox("快捷键配置")
        hotkey_group.setStyleSheet("""
            QGroupBox {
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
            }
        """)
        hotkey_layout = QGridLayout(hotkey_group)
        hotkey_layout.setSpacing(12)
        hotkey_layout.setColumnStretch(0, 0)
        hotkey_layout.setColumnStretch(1, 1)
        hotkey_layout.setColumnStretch(2, 0)

        # Create hotkey inputs
        row = 0
        for key_name, display_name, description in self.settings_manager.HOTKEYS:
            # Label
            label = QLabel(display_name)
            label.setStyleSheet("color: #d4d4d4; font-size: 13px;")
            label.setToolTip(description)
            hotkey_layout.addWidget(label, row, 0)

            # Hotkey capture edit
            hotkey_edit = HotkeyCaptureEdit()
            hotkey_edit.setMinimumWidth(180)
            hotkey_edit.setStyleSheet("""
                QLineEdit {
                    background-color: #3c3c3c;
                    color: #d4d4d4;
                    border: 1px solid #3e3e3e;
                    border-radius: 4px;
                    padding: 8px;
                    font-size: 13px;
                }
                QLineEdit:focus {
                    border-color: #007acc;
                }
            """)
            self.hotkey_edits[key_name] = hotkey_edit
            hotkey_layout.addWidget(hotkey_edit, row, 1)

            # Reset button
            reset_btn = QPushButton("恢复默认")
            reset_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3c3c3c;
                    color: #d4d4d4;
                    border: 1px solid #3e3e3e;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 12px;
                    min-width: 70px;
                }
                QPushButton:hover {
                    background-color: #4e4e4e;
                    border-color: #007acc;
                }
            """)
            reset_btn.clicked.connect(lambda checked, k=key_name: self._reset_hotkey(k))
            hotkey_layout.addWidget(reset_btn, row, 2)

            row += 1

        scroll_layout.addWidget(hotkey_group)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)

        # Conflict warning label
        self.conflict_label = QLabel()
        self.conflict_label.setStyleSheet("color: #ff6b6b; font-size: 12px;")
        self.conflict_label.setWordWrap(True)
        self.conflict_label.hide()
        layout.addWidget(self.conflict_label)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        # Style buttons
        ok_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("确定")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)

        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4e4e4e;
                border-color: #007acc;
            }
        """)

        layout.addWidget(button_box)

    def _load_settings(self):
        """Load current hotkey settings."""
        settings = self.settings_manager.settings

        # Load enable state
        self.enable_checkbox.setChecked(
            self.settings_manager.get('hotkey_enabled', True)
        )

        # Load hotkeys
        defaults = {
            'hotkey': 'ctrl+shift+o',
            'hotkey_copy': 'ctrl+c',
            'hotkey_save': 'ctrl+s',
            'hotkey_edit': 'ctrl+e',
        }

        for key_name in self.hotkey_edits:
            hotkey = self.settings_manager.get(key_name, defaults.get(key_name, ''))
            self.original_hotkeys[key_name] = hotkey
            self.hotkey_edits[key_name].set_hotkey(hotkey)

    def _reset_hotkey(self, key_name: str):
        """Reset a hotkey to its default value."""
        defaults = {
            'hotkey': 'ctrl+shift+o',
            'hotkey_copy': 'ctrl+c',
            'hotkey_save': 'ctrl+s',
            'hotkey_edit': 'ctrl+e',
        }
        default_value = defaults.get(key_name, '')
        self.hotkey_edits[key_name].set_hotkey(default_value)
        self.conflict_label.hide()

    def _validate_hotkeys(self) -> tuple[bool, str]:
        """Validate all hotkey settings."""
        new_hotkeys = {}

        # Collect all hotkeys
        for key_name, edit in self.hotkey_edits.items():
            hotkey = edit.get_hotkey().strip().lower()
            if hotkey:
                new_hotkeys[key_name] = hotkey

        # Validate each hotkey
        for key_name, hotkey in new_hotkeys.items():
            is_valid, error = self.settings_manager.validate_hotkey(hotkey)
            if not is_valid:
                display_name = dict(self.settings_manager.HOTKEYS).get(key_name, key_name)
                return False, f"{display_name}: {error}"

        # Check for conflicts
        conflicts = self.settings_manager.check_hotkey_conflicts(new_hotkeys)
        if conflicts:
            conflict_names = []
            for key1, key2, hotkey in conflicts:
                name1 = dict(self.settings_manager.HOTKEYS).get(key1, key1)
                name2 = dict(self.settings_manager.HOTKEYS).get(key2, key2)
                conflict_names.append(f"{name1} 和 {name2} ({hotkey})")
            return False, f"快捷键冲突: {', '.join(conflict_names)}"

        return True, ""

    def _on_accept(self):
        """Handle OK button click."""
        is_valid, error = self._validate_hotkeys()

        if not is_valid:
            self.conflict_label.setText(error)
            self.conflict_label.show()
            QMessageBox.warning(self, "验证失败", error)
            return

        # Save settings
        self.settings_manager.set('hotkey_enabled', self.enable_checkbox.isChecked())

        new_hotkeys = {}
        for key_name, edit in self.hotkey_edits.items():
            hotkey = edit.get_hotkey().strip().lower()
            self.settings_manager.set(key_name, hotkey)
            new_hotkeys[key_name] = hotkey

        self.settings_manager.save()

        # Emit signal with new hotkeys
        self.hotkeys_changed.emit(new_hotkeys)

        self.accept()

    def get_hotkey_changes(self) -> dict:
        """Get the changed hotkeys."""
        changes = {}
        for key_name, edit in self.hotkey_edits.items():
            new_hotkey = edit.get_hotkey().strip().lower()
            old_hotkey = self.original_hotkeys.get(key_name, '')
            if new_hotkey != old_hotkey:
                changes[key_name] = new_hotkey
        return changes
