#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ScreenOCR - Settings Manager
Manages application settings with persistence.
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class AppSettings:
    """Application settings data class."""
    # OCR Language: 'ch' (Chinese), 'en' (English), 'ch_en' (Chinese+English)
    ocr_language: str = 'ch'

    # OCR Model: 'pp-ocrv5' (fast), 'paddleocr-vl' (accurate, VL model)
    ocr_model: str = 'pp-ocrv5'

    # Global hotkey for screenshot
    hotkey: str = 'ctrl+shift+o'

    # Additional hotkeys
    hotkey_copy: str = 'ctrl+c'           # Copy result
    hotkey_save: str = 'ctrl+s'           # Save result
    hotkey_edit: str = 'ctrl+e'           # Toggle edit mode

    # Theme: 'dark' or 'light'
    theme: str = 'dark'

    # Default device: 'cpu', 'gpu:0', 'gpu:1', etc.
    default_device: str = 'cpu'

    # Auto copy to clipboard after OCR
    auto_copy: bool = True

    # Show notification after OCR
    show_notification: bool = True

    # Minimize to tray on close
    minimize_to_tray: bool = True

    # Start minimized
    start_minimized: bool = False

    # History max records
    history_max_records: int = 500

    # Enable/disable hotkeys
    hotkey_enabled: bool = True

    # PP-StructureV3 Document Mode Settings
    doc_use_table_recognition: bool = True      # Table structure recognition
    doc_use_formula_recognition: bool = False   # LaTeX formula recognition
    doc_use_seal_recognition: bool = False      # Seal/stamp detection
    doc_use_chart_recognition: bool = False     # Chart recognition
    doc_use_doc_orientation: bool = False       # Document orientation fix
    doc_use_doc_unwarping: bool = False         # Document unwarping/dewarp


class SettingsManager:
    """
    Settings manager with JSON persistence.
    Settings are saved to %LOCALAPPDATA%/ScreenOCR/settings.json
    """

    # Available OCR languages (only Chinese and English)
    LANGUAGES = [
        ('ch', '简体中文'),
        ('en', 'English'),
    ]

    # Available OCR models
    OCR_MODELS = [
        ('pp-ocrv5', 'PP-OCRv5 (快速，适合普通场景)'),
        ('paddleocr-vl', 'PaddleOCR-VL-1.5 (精准，适合复杂场景)'),
    ]

    # Available themes
    THEMES = [
        ('dark', '深色主题'),
        ('light', '浅色主题'),
    ]

    # Hotkey definitions (key, display_name, description)
    HOTKEYS = [
        ('hotkey', '截图快捷键', '触发截图识别的全局快捷键'),
        ('hotkey_copy', '复制结果', '复制识别结果到剪贴板'),
        ('hotkey_save', '保存结果', '保存识别结果到文件'),
        ('hotkey_edit', '编辑模式', '切换文本编辑模式'),
    ]

    # Reserved system shortcuts that cannot be used
    RESERVED_HOTKEYS = [
        'ctrl+alt+delete',  # Windows security
        'ctrl+shift+esc',   # Task manager
        'alt+f4',           # Close window
        'alt+tab',          # Switch window
        'win',              # Windows key
        'win+l',            # Lock screen
        'win+d',            # Show desktop
        'win+e',            # Explorer
        'win+r',            # Run dialog
        'print',            # Screenshot
        'ctrl+alt+tab',     # Switch window
        'esc',              # ESC key - used for canceling screenshot overlay
    ]

    def __init__(self):
        self._settings = AppSettings()
        self._settings_file = self._get_settings_path()
        self._load()

    def _get_settings_path(self) -> str:
        """Get the settings file path."""
        if os.name == 'nt':
            app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        else:
            app_data = os.path.expanduser('~/.config')

        settings_dir = os.path.join(app_data, 'ScreenOCR')
        os.makedirs(settings_dir, exist_ok=True)

        return os.path.join(settings_dir, 'settings.json')

    def _load(self):
        """Load settings from file."""
        if os.path.exists(self._settings_file):
            try:
                with open(self._settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Update settings with loaded values
                for key, value in data.items():
                    if hasattr(self._settings, key):
                        setattr(self._settings, key, value)

            except (json.JSONDecodeError, IOError) as e:
                print(f"[WARNING] Failed to load settings: {e}")

    def save(self):
        """Save settings to file."""
        try:
            with open(self._settings_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self._settings), f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[ERROR] Failed to save settings: {e}")

    @property
    def settings(self) -> AppSettings:
        """Get current settings."""
        return self._settings

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return getattr(self._settings, key, default)

    def set(self, key: str, value: Any):
        """Set a setting value."""
        if hasattr(self._settings, key):
            setattr(self._settings, key, value)

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self._settings = AppSettings()
        self.save()

    def validate_hotkey(self, hotkey: str) -> tuple[bool, str]:
        """
        Validate a hotkey string.
        Returns (is_valid, error_message).
        """
        if not hotkey or not hotkey.strip():
            return False, "快捷键不能为空"

        hotkey = hotkey.strip().lower()

        # Check reserved system shortcuts
        if hotkey in self.RESERVED_HOTKEYS:
            return False, f"'{hotkey}' 是系统保留快捷键，无法使用"

        # Check format (must contain at least one modifier or be a function key)
        valid_modifiers = ['ctrl', 'alt', 'shift', 'win']
        valid_keys = [
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
            'esc', 'tab', 'space', 'enter', 'backspace', 'delete', 'insert',
            'home', 'end', 'pageup', 'pagedown', 'up', 'down', 'left', 'right',
            'print', 'scrolllock', 'pause', 'numlock',
            '`', '-', '=', '[', ']', '\\', ';', "'", ',', '.', '/'
        ]

        parts = hotkey.split('+')
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) == 0:
            return False, "快捷键格式无效"

        # Check if last part is a valid key
        last_part = parts[-1]
        has_modifier = any(p in valid_modifiers for p in parts[:-1])
        is_function_key = last_part.startswith('f') and last_part[1:].isdigit()
        is_valid_key = last_part in valid_keys

        if not is_valid_key:
            return False, f"无效的按键: '{last_part}'"

        # Function keys can be used without modifiers
        if is_function_key:
            return True, ""

        # Other keys need at least one modifier
        if not has_modifier:
            return False, "快捷键必须包含至少一个修饰键 (Ctrl/Alt/Shift/Win)"

        return True, ""

    def check_hotkey_conflicts(self, new_hotkeys: dict) -> list[tuple[str, str, str]]:
        """
        Check for conflicts among hotkeys.
        Returns list of (hotkey1_name, hotkey2_name, hotkey_value) conflicts.
        """
        conflicts = []
        seen = {}

        for key_name, hotkey in new_hotkeys.items():
            normalized = hotkey.strip().lower()
            if normalized in seen:
                conflicts.append((seen[normalized], key_name, normalized))
            else:
                seen[normalized] = key_name

        return conflicts

    def get_hotkey_display_name(self, hotkey: str) -> str:
        """Get display name for a hotkey."""
        if not hotkey:
            return ""

        parts = hotkey.split('+')
        display_parts = []

        for part in parts:
            part = part.strip()
            if part.lower() == 'ctrl':
                display_parts.append('Ctrl')
            elif part.lower() == 'alt':
                display_parts.append('Alt')
            elif part.lower() == 'shift':
                display_parts.append('Shift')
            elif part.lower() == 'win':
                display_parts.append('Win')
            elif part.lower().startswith('f') and part[1:].isdigit():
                display_parts.append(part.upper())
            else:
                display_parts.append(part.capitalize())

        return '+'.join(display_parts)
