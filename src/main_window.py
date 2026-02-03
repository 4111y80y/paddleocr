#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ScreenOCR - Main Window
"""

import logging
import sys
import os
import tempfile

# Setup logging for debugging
log_file = os.path.join(tempfile.gettempdir(), "screenocr_batch.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QStatusBar, QSplitter, QLabel,
    QTextEdit, QGroupBox, QPushButton, QComboBox,
    QMessageBox, QListWidget, QListWidgetItem, QDialog,
    QDialogButtonBox, QLineEdit, QScrollArea, QFrame,
    QProgressBar
)
from PySide6.QtCore import Qt, QSize, Signal, QObject, QThread
from PySide6.QtGui import QAction, QIcon, QPixmap, QImage, QColor


class OCRWorker(QObject):
    """Worker for running OCR in a background thread.

    [Task 763] Changed from QTimer (main thread) to QThread (background thread)
    to prevent UI freezing during OCR operations.
    """
    finished = Signal(str, float, list)  # (result_text, elapsed_time, confidence_items)
    error = Signal(str)  # error message

    def __init__(self, ocr_engine, image_path):
        super().__init__()
        self.ocr_engine = ocr_engine
        self.image_path = image_path

    def run(self):
        """Execute OCR in background thread."""
        import time
        try:
            start_time = time.time()

            # Use regular OCR
            confidence_items = self.ocr_engine.recognize_with_confidence(self.image_path)
            result_text = '\n'.join([item[0] for item in confidence_items])

            elapsed = time.time() - start_time

            self.finished.emit(result_text, elapsed, confidence_items)
        except Exception as e:
            self.error.emit(str(e))


class DocumentOCRWorker(QObject):
    """Worker for running document structure analysis using PP-StructureV3 in background thread.

    [Task 763] Changed from QTimer (main thread) to QThread (background thread)
    to prevent UI freezing during document analysis operations.
    """
    finished = Signal(str, float)  # (markdown_result, elapsed_time)
    error = Signal(str)  # error message

    def __init__(self, ocr_engine, image_path, doc_settings=None):
        super().__init__()
        self.ocr_engine = ocr_engine
        self.image_path = image_path
        self.doc_settings = doc_settings

    def run(self):
        """Execute document structure analysis in background thread."""
        import time
        try:
            start_time = time.time()

            # Use PP-StructureV3 for document analysis
            result = self.ocr_engine.recognize_document(self.image_path, self.doc_settings)

            elapsed = time.time() - start_time

            self.finished.emit(result, elapsed)
        except Exception as e:
            self.error.emit(str(e))


class BatchOCRWorker(QObject):
    """Worker for running batch OCR - processes files one at a time using QTimer."""
    progress = Signal(int, int, str)  # (current, total, current_file)
    fileFinished = Signal(int, str, str, float, list)  # (index, file_path, result_text, elapsed, confidence_items)
    finished = Signal()  # all files done
    error = Signal(int, str, str)  # (index, file_path, error_msg)

    def __init__(self, ocr_engine, file_paths, parent=None):
        super().__init__(parent)
        self.ocr_engine = ocr_engine
        self.file_paths = file_paths
        self._stopped = False
        self._current_index = 0
        self._timer = None

    def stop(self):
        """Stop the batch processing."""
        self._stopped = True
        if self._timer:
            self._timer.stop()

    def start(self):
        """Start processing files one at a time."""
        from PySide6.QtCore import QTimer
        self._current_index = 0
        self._stopped = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_next_file)
        self._timer.setSingleShot(True)
        self._timer.start(10)  # Start after 10ms

    def _process_next_file(self):
        """Process the next file in the queue."""
        import time

        if self._stopped or self._current_index >= len(self.file_paths):
            logger.info("[BatchOCR] Batch processing finished")
            self.finished.emit()
            return

        file_path = self.file_paths[self._current_index]
        total = len(self.file_paths)
        i = self._current_index

        logger.debug(f"[BatchOCR] Processing file {i+1}/{total}: {file_path}")
        self.progress.emit(i + 1, total, file_path)

        try:
            start_time = time.time()
            confidence_items = self.ocr_engine.recognize_with_confidence(file_path)
            elapsed = time.time() - start_time
            result_text = '\n'.join([item[0] for item in confidence_items])

            logger.debug(f"[BatchOCR] File {i+1} completed: {len(result_text)} chars, {elapsed:.2f}s")
            self.fileFinished.emit(i, file_path, result_text, elapsed, confidence_items)
        except Exception as e:
            logger.error(f"[BatchOCR] Error processing file {i+1}: {e}")
            self.error.emit(i, file_path, str(e))

        self._current_index += 1

        # Schedule next file processing
        if not self._stopped and self._current_index < len(self.file_paths):
            self._timer.start(10)
        else:
            logger.info("[BatchOCR] Batch processing finished")
            self.finished.emit()

from ocr_engine import OCREngine
from screenshot_overlay import ScreenshotOverlay
from history_manager import HistoryManager
from settings import SettingsManager, AppSettings


class ImagePreviewWidget(QWidget):
    """Widget for displaying screenshot preview."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._pixmap = None

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Header with title
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("截图预览")
        title_label.setStyleSheet("""
            QLabel {
                color: #d4d4d4;
                font-weight: bold;
                font-size: 14px;
                padding: 4px 0;
            }
        """)
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)

        # Image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #252526;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                color: #6e6e6e;
            }
        """)
        self.image_label.setMinimumSize(200, 200)
        self.image_label.setText("暂无截图")

        layout.addWidget(self.image_label)

    def set_image(self, image):
        """Set image from PIL Image or QImage."""
        if image is None:
            self._pixmap = None
            self.image_label.setText("暂无截图")
            return

        # Convert PIL Image to QPixmap
        if hasattr(image, 'tobytes'):
            # PIL Image
            data = image.convert('RGBA').tobytes('raw', 'RGBA')
            qimage = QImage(
                data, image.width, image.height,
                QImage.Format.Format_RGBA8888
            )
            self._pixmap = QPixmap.fromImage(qimage)
        elif isinstance(image, QImage):
            self._pixmap = QPixmap.fromImage(image)
        elif isinstance(image, QPixmap):
            self._pixmap = image
        else:
            return

        self._update_display()

    def _update_display(self):
        """Update the displayed image, scaling to fit."""
        if self._pixmap is None:
            return

        label_size = self.image_label.size()
        scaled = self._pixmap.scaled(
            label_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap:
            self._update_display()


class ResultTextWidget(QWidget):
    """Widget for displaying and editing OCR results with confidence scores."""

    copyRequested = Signal()
    saveRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.confidence_items = []  # Store (text, confidence) tuples
        self.confidence_threshold = 0.8  # Default threshold
        self.show_confidence = True  # Show confidence by default
        self._is_editable = False  # Edit mode toggle
        self._plain_text_backup = ""  # Backup for plain text when switching modes
        self._smart_layout = False  # Smart layout mode (disabled by default)
        self._merged_text = ""  # Merged text for smart layout
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Header with confidence controls and copy button
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        # Title label with consistent styling
        title_label = QLabel("识别结果")
        title_label.setStyleSheet("""
            QLabel {
                color: #d4d4d4;
                font-weight: bold;
                font-size: 14px;
                padding: 4px 0;
            }
        """)
        header.addWidget(title_label)

        # Confidence threshold control
        threshold_label = QLabel("置信度阈值:")
        threshold_label.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        header.addWidget(threshold_label)

        self.threshold_combo = QComboBox()
        self.threshold_combo.setFixedWidth(80)
        self.threshold_combo.setStyleSheet("""
            QComboBox {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #d4d4d4;
                selection-background-color: #0e639c;
            }
        """)
        # Add threshold options (0.5 - 0.95)
        for threshold in [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]:
            self.threshold_combo.addItem(f"{threshold:.0%}", threshold)
        # Set default to 0.8 (index 4)
        self.threshold_combo.setCurrentIndex(4)
        self.threshold_combo.currentIndexChanged.connect(self.on_threshold_changed)
        header.addWidget(self.threshold_combo)

        # Show/hide confidence toggle
        self.confidence_toggle = QPushButton("显示置信度")
        self.confidence_toggle.setCheckable(True)
        self.confidence_toggle.setChecked(True)
        self.confidence_toggle.setFixedWidth(90)
        self.confidence_toggle.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 12px;
            }
            QPushButton:checked {
                background-color: #0e639c;
                border-color: #1177bb;
            }
            QPushButton:hover {
                border-color: #007acc;
            }
        """)
        self.confidence_toggle.clicked.connect(self.on_toggle_confidence)
        header.addWidget(self.confidence_toggle)

        # Confidence legend
        legend_label = QLabel("低置信度: <80%")
        legend_label.setStyleSheet("""
            QLabel {
                color: #ffcc00;
                font-size: 11px;
                padding: 2px 6px;
                background-color: rgba(255, 204, 0, 0.15);
                border-radius: 3px;
            }
        """)
        header.addWidget(legend_label)

        header.addStretch()

        # Edit mode toggle button
        self.edit_toggle_btn = QPushButton("编辑")
        self.edit_toggle_btn.setCheckable(True)
        self.edit_toggle_btn.setFixedSize(70, 28)
        self.edit_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555555;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:checked {
                background-color: #0e639c;
                border-color: #1177bb;
            }
            QPushButton:hover {
                border-color: #007acc;
            }
        """)
        self.edit_toggle_btn.clicked.connect(self.on_toggle_edit_mode)
        header.addWidget(self.edit_toggle_btn)

        # Undo/Redo buttons (visible only in edit mode)
        self.undo_btn = QPushButton("撤销")
        self.undo_btn.setFixedSize(60, 28)
        self.undo_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555555;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
                border-color: #007acc;
            }
            QPushButton:disabled {
                color: #6e6e6e;
            }
        """)
        self.undo_btn.clicked.connect(self.on_undo)
        self.undo_btn.setVisible(False)
        header.addWidget(self.undo_btn)

        self.redo_btn = QPushButton("重做")
        self.redo_btn.setFixedSize(60, 28)
        self.redo_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555555;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
                border-color: #007acc;
            }
            QPushButton:disabled {
                color: #6e6e6e;
            }
        """)
        self.redo_btn.clicked.connect(self.on_redo)
        self.redo_btn.setVisible(False)
        header.addWidget(self.redo_btn)

        # Save button (visible only in edit mode)
        self.save_btn = QPushButton("保存")
        self.save_btn.setFixedSize(70, 28)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
            QPushButton:pressed {
                background-color: #1a7f2e;
            }
        """)
        self.save_btn.clicked.connect(self.saveRequested.emit)
        self.save_btn.setVisible(False)
        header.addWidget(self.save_btn)

        header.addStretch()

        self.copy_btn = QPushButton("复制")
        self.copy_btn.setFixedSize(80, 28)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #0d5a8c;
            }
        """)
        self.copy_btn.clicked.connect(self.copyRequested.emit)
        header.addWidget(self.copy_btn)

        layout.addLayout(header)

        # Normal text area
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("识别结果将显示在这里...")
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px;
                font-family: "Consolas", "Microsoft YaHei UI", monospace;
                font-size: 14px;
            }
            QTextEdit[editable="true"] {
                background-color: #1e1e1e;
                border: 1px solid #007acc;
            }
        """)
        layout.addWidget(self.text_edit)

    def on_threshold_changed(self, index):
        """Handle confidence threshold change."""
        self.confidence_threshold = self.threshold_combo.currentData()
        self.refresh_display()

    def on_toggle_confidence(self, checked):
        """Toggle confidence display on/off."""
        self.show_confidence = checked
        self.refresh_display()

    def on_toggle_edit_mode(self, checked):
        """Toggle edit mode on/off."""
        self._is_editable = checked

        if checked:
            # Enter edit mode
            self._plain_text_backup = self.get_text()
            self.text_edit.setReadOnly(False)
            self.text_edit.setProperty("editable", "true")
            self.text_edit.setPlainText(self._plain_text_backup)
            self.text_edit.style().unpolish(self.text_edit)
            self.text_edit.style().polish(self.text_edit)
            self.edit_toggle_btn.setText("完成")
            # Show edit controls
            self.undo_btn.setVisible(True)
            self.redo_btn.setVisible(True)
            self.save_btn.setVisible(True)
            # Hide confidence controls in edit mode
            self.threshold_combo.setEnabled(False)
            self.confidence_toggle.setEnabled(False)
            # Note: time_label belongs to MainWindow, not ResultTextWidget
        else:
            # Exit edit mode
            self.text_edit.setReadOnly(True)
            self.text_edit.setProperty("editable", "false")
            self.text_edit.style().unpolish(self.text_edit)
            self.text_edit.style().polish(self.text_edit)
            self.edit_toggle_btn.setText("编辑")
            # Hide edit controls
            self.undo_btn.setVisible(False)
            self.redo_btn.setVisible(False)
            self.save_btn.setVisible(False)
            # Re-enable confidence controls
            self.threshold_combo.setEnabled(True)
            self.confidence_toggle.setEnabled(True)
            # Refresh display with confidence formatting
            self.refresh_display()

    def on_undo(self):
        """Undo last edit action."""
        self.text_edit.undo()

    def on_redo(self):
        """Redo last undone action."""
        self.text_edit.redo()

    def save_to_file(self):
        """Save edited text to file. Returns True if saved successfully."""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存文本",
            "",
            "文本文件 (*.txt);;所有文件 (*)"
        )

        if file_path:
            try:
                text = self.text_edit.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                return True, file_path
            except Exception as e:
                return False, str(e)
        return False, None

    def set_confidence_items(self, items):
        """Set the OCR result with confidence scores."""
        self.confidence_items = items
        self.refresh_display()

    def refresh_display(self):
        """Refresh the display with current confidence settings."""
        # If smart layout is enabled and we have merged text, display it
        if self._smart_layout and self._merged_text:
            self.text_edit.setPlainText(self._merged_text)
            return

        if not self.confidence_items:
            return

        self.text_edit.clear()
        cursor = self.text_edit.textCursor()

        for i, (text, confidence) in enumerate(self.confidence_items):
            # Determine text color based on confidence
            if confidence < 0.6:
                color = "#ff6b6b"  # Red for very low confidence
            elif confidence < self.confidence_threshold:
                color = "#ffcc00"  # Yellow for low confidence
            else:
                color = "#d4d4d4"  # Normal color for good confidence

            # Create formatted text
            if self.show_confidence:
                display_text = f"[{confidence:.1%}] {text}"
            else:
                display_text = text

            # Insert with color
            char_format = cursor.charFormat()
            char_format.setForeground(QColor(color))
            cursor.setCharFormat(char_format)
            cursor.insertText(display_text)

            # Add newline between items
            if i < len(self.confidence_items) - 1:
                cursor.insertText("\n")

        self.text_edit.setTextCursor(cursor)

    def set_text(self, text):
        """Set the OCR result text (fallback for plain text)."""
        self.text_edit.setPlainText(text)

    def get_text(self):
        """Get the OCR result text (without confidence markers)."""
        if self.confidence_items:
            return '\n'.join([item[0] for item in self.confidence_items])
        return self.text_edit.toPlainText()

    def clear(self):
        """Clear the text and confidence items."""
        self.text_edit.clear()
        self.confidence_items = []


class DocumentResultWidget(QWidget):
    """Widget for displaying document structure analysis results (Markdown only)."""

    copyRequested = Signal()
    exportMarkdownRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.markdown_text = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Header with export buttons
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        # Title label
        title_label = QLabel("文档解析结果 (Markdown)")
        title_label.setStyleSheet("""
            QLabel {
                color: #d4d4d4;
                font-weight: bold;
                font-size: 14px;
                padding: 4px 0;
            }
        """)
        header.addWidget(title_label)

        header.addStretch()

        # Copy button
        self.copy_btn = QPushButton("复制")
        self.copy_btn.setFixedSize(70, 28)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)
        self.copy_btn.clicked.connect(self.copyRequested.emit)
        header.addWidget(self.copy_btn)

        # Export button
        self.export_md_btn = QPushButton("导出 Markdown")
        self.export_md_btn.setFixedSize(110, 28)
        self.export_md_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
        """)
        self.export_md_btn.clicked.connect(self.exportMarkdownRequested.emit)
        header.addWidget(self.export_md_btn)

        layout.addLayout(header)

        # Text area for displaying results
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("文档解析结果将显示在这里...")
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px;
                font-family: "Consolas", "Microsoft YaHei UI", monospace;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.text_edit)

        # Info label
        self.info_label = QLabel("使用 PP-StructureV3 进行文档结构分析")
        self.info_label.setStyleSheet("color: #6e6e6e; font-size: 11px;")
        layout.addWidget(self.info_label)

    def set_markdown(self, markdown: str):
        """Set the markdown text."""
        self.markdown_text = markdown
        self.text_edit.setPlainText(markdown)

    def get_markdown(self) -> str:
        """Get the markdown text."""
        return self.markdown_text

    def clear(self):
        """Clear the results."""
        self.text_edit.clear()
        self.markdown_text = ""


class HistoryDialog(QDialog):
    """Dialog for viewing and managing OCR history."""

    def __init__(self, history_manager, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager
        self.selected_record = None
        self.setup_ui()
        self.load_history()

    def setup_ui(self):
        """Setup dialog UI."""
        self.setWindowTitle("历史记录")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索内容...")
        self.search_input.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_input)

        self.clear_btn = QPushButton("清空全部")
        self.clear_btn.clicked.connect(self.clear_all_history)
        search_layout.addWidget(self.clear_btn)

        layout.addLayout(search_layout)

        # History list
        self.history_list = QListWidget()
        self.history_list.setAlternatingRowColors(True)
        self.history_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #2d2d2d;
            }
            QListWidget::item:alternate {
                background-color: #252526;
            }
            QListWidget::item:selected {
                background-color: #0e639c;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #2a2d2e;
            }
        """)
        self.history_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.history_list.currentItemChanged.connect(self.on_item_selected)
        layout.addWidget(self.history_list)

        # Preview area
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(150)
        preview_layout.addWidget(self.preview_text)
        layout.addWidget(preview_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.copy_btn = QPushButton("复制文本")
        self.copy_btn.clicked.connect(self.copy_selected)
        button_layout.addWidget(self.copy_btn)

        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.delete_selected)
        button_layout.addWidget(self.delete_btn)

        button_layout.addStretch()

        self.restore_btn = QPushButton("恢复")
        self.restore_btn.clicked.connect(self.restore_selected)
        button_layout.addWidget(self.restore_btn)

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

    def load_history(self, query: str = ""):
        """Load history records into list."""
        self.history_list.clear()

        if query:
            records = self.history_manager.search(query)
        else:
            records = self.history_manager.get_records(limit=100)

        for record in records:
            # Create list item with timestamp and text preview
            text_preview = record.text[:80].replace('\n', ' ')
            if len(record.text) > 80:
                text_preview += "..."

            item_text = f"[{record.timestamp}] {text_preview}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, record.id)
            self.history_list.addItem(item)

        count = self.history_manager.get_count()
        self.status_label.setText(f"共 {count} 条记录")

    def on_search(self, text):
        """Handle search input change."""
        self.load_history(text)

    def on_item_selected(self, current, previous):
        """Handle item selection change."""
        if current:
            record_id = current.data(Qt.ItemDataRole.UserRole)
            record = self.history_manager.get_record_by_id(record_id)
            if record:
                self.preview_text.setPlainText(record.text)

    def on_item_double_clicked(self, item):
        """Handle double click on item - restore it."""
        self.restore_selected()

    def copy_selected(self):
        """Copy selected record text to clipboard."""
        from PySide6.QtWidgets import QApplication

        current = self.history_list.currentItem()
        if current:
            record_id = current.data(Qt.ItemDataRole.UserRole)
            record = self.history_manager.get_record_by_id(record_id)
            if record:
                clipboard = QApplication.clipboard()
                clipboard.setText(record.text)
                self.status_label.setText("已复制到剪贴板！")

    def delete_selected(self):
        """Delete selected record."""
        current = self.history_list.currentItem()
        if current:
            record_id = current.data(Qt.ItemDataRole.UserRole)
            reply = QMessageBox.question(
                self, "确认删除",
                "确定要删除这条记录吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.history_manager.delete_record(record_id)
                self.load_history(self.search_input.text())
                self.preview_text.clear()

    def restore_selected(self):
        """Restore selected record to main window."""
        current = self.history_list.currentItem()
        if current:
            record_id = current.data(Qt.ItemDataRole.UserRole)
            record = self.history_manager.get_record_by_id(record_id)
            if record:
                self.selected_record = record
                self.accept()

    def clear_all_history(self):
        """Clear all history records."""
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要删除所有历史记录吗？\n此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history_manager.clear_all()
            self.load_history()
            self.preview_text.clear()


class BatchOCRDialog(QDialog):
    """Dialog for batch OCR processing."""

    def __init__(self, ocr_engine, parent=None):
        super().__init__(parent)
        self.ocr_engine = ocr_engine
        self.file_paths = []
        self.results = []  # Store (file_path, result_text, elapsed) tuples
        self._batch_worker = None  # No thread needed
        self.setup_ui()

    def setup_ui(self):
        """Setup dialog UI."""
        self.setWindowTitle("批量 OCR 处理")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # File selection area
        file_group = QGroupBox("文件选择")
        file_layout = QVBoxLayout(file_group)

        # File list
        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        self.file_list.setStyleSheet("""
            QListWidget {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #3e3e3e;
            }
            QListWidget::item:selected {
                background-color: #0e639c;
            }
        """)
        file_layout.addWidget(self.file_list)

        # File buttons
        file_btn_layout = QHBoxLayout()

        self.add_files_btn = QPushButton("添加文件")
        self.add_files_btn.clicked.connect(self.add_files)
        self.add_files_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
                border-color: #007acc;
            }
        """)
        file_btn_layout.addWidget(self.add_files_btn)

        self.clear_files_btn = QPushButton("清空列表")
        self.clear_files_btn.clicked.connect(self.clear_files)
        self.clear_files_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
                border-color: #007acc;
            }
        """)
        file_btn_layout.addWidget(self.clear_files_btn)

        file_btn_layout.addStretch()

        self.remove_file_btn = QPushButton("移除选中")
        self.remove_file_btn.clicked.connect(self.remove_selected_file)
        self.remove_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
                border-color: #007acc;
            }
        """)
        file_btn_layout.addWidget(self.remove_file_btn)

        file_layout.addLayout(file_btn_layout)
        layout.addWidget(file_group)

        # Progress area
        progress_group = QGroupBox("处理进度")
        progress_layout = QVBoxLayout(progress_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                text-align: center;
                height: 24px;
            }
            QProgressBar::chunk {
                background-color: #0e639c;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("就绪 - 请选择要处理的图片文件")
        self.status_label.setStyleSheet("color: #a0a0a0;")
        progress_layout.addWidget(self.status_label)

        # Current file label
        self.current_file_label = QLabel("")
        self.current_file_label.setStyleSheet("color: #6e6e6e; font-size: 11px;")
        self.current_file_label.setWordWrap(True)
        progress_layout.addWidget(self.current_file_label)

        layout.addWidget(progress_group)

        # Results summary
        self.results_summary = QTextEdit()
        self.results_summary.setPlaceholderText("处理结果将显示在这里...")
        self.results_summary.setReadOnly(True)
        self.results_summary.setMaximumHeight(150)
        self.results_summary.setStyleSheet("""
            QTextEdit {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px;
                font-family: "Consolas", "Microsoft YaHei UI", monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.results_summary)

        # Buttons
        button_layout = QHBoxLayout()

        self.export_btn = QPushButton("导出结果")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
            QPushButton:disabled {
                background-color: #3e3e3e;
                color: #6e6e6e;
            }
        """)
        button_layout.addWidget(self.export_btn)

        button_layout.addStretch()

        self.start_btn = QPushButton("开始处理")
        self.start_btn.clicked.connect(self.start_batch_processing)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:disabled {
                background-color: #3e3e3e;
                color: #6e6e6e;
            }
        """)
        button_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_batch_processing)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #da3633;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #f85149;
            }
            QPushButton:disabled {
                background-color: #3e3e3e;
                color: #6e6e6e;
            }
        """)
        button_layout.addWidget(self.stop_btn)

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.reject)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
                border-color: #007acc;
            }
        """)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def add_files(self):
        """Add image files to the list."""
        from PySide6.QtWidgets import QFileDialog

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片文件",
            "",
            "图片 (*.png *.jpg *.jpeg *.bmp *.gif *.tiff);;所有文件 (*)"
        )

        for file_path in files:
            if file_path not in self.file_paths:
                self.file_paths.append(file_path)
                item = QListWidgetItem(file_path)
                self.file_list.addItem(item)

        self.update_status()

    def remove_selected_file(self):
        """Remove selected file from the list."""
        current_row = self.file_list.currentRow()
        if current_row >= 0:
            self.file_list.takeItem(current_row)
            del self.file_paths[current_row]
        self.update_status()

    def clear_files(self):
        """Clear all files from the list."""
        self.file_paths.clear()
        self.file_list.clear()
        self.results.clear()
        self.update_status()
        self.export_btn.setEnabled(False)

    def update_status(self):
        """Update status label."""
        count = len(self.file_paths)
        if count == 0:
            self.status_label.setText("就绪 - 请选择要处理的图片文件")
        else:
            self.status_label.setText(f"已选择 {count} 个文件")

    def start_batch_processing(self):
        """Start batch OCR processing."""
        if not self.file_paths:
            QMessageBox.warning(self, "警告", "请先选择要处理的图片文件")
            return

        if not self.ocr_engine:
            QMessageBox.critical(self, "错误", "OCR 引擎未初始化")
            return

        # Clear previous results
        self.results.clear()
        self.results_summary.clear()

        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.add_files_btn.setEnabled(False)
        self.clear_files_btn.setEnabled(False)
        self.remove_file_btn.setEnabled(False)
        self.export_btn.setEnabled(False)

        self.progress_bar.setMaximum(len(self.file_paths))
        self.progress_bar.setValue(0)

        # Clean up any previous worker
        if self._batch_worker:
            self._batch_worker.stop()
            self._batch_worker = None

        # Create worker (no thread needed - uses QTimer)
        self._batch_worker = BatchOCRWorker(self.ocr_engine, self.file_paths, parent=self)

        # Connect signals
        self._batch_worker.progress.connect(self.on_batch_progress)
        self._batch_worker.fileFinished.connect(self.on_file_finished)
        self._batch_worker.error.connect(self.on_batch_error)
        self._batch_worker.finished.connect(self.on_batch_finished)

        # Start processing
        self._batch_worker.start()

    def stop_batch_processing(self):
        """Stop batch OCR processing."""
        if self._batch_worker:
            self._batch_worker.stop()
        self.status_label.setText("正在停止...")

    def on_batch_progress(self, current, total, current_file):
        """Handle batch progress update."""
        self.progress_bar.setValue(current - 1)
        self.status_label.setText(f"正在处理: {current}/{total}")
        self.current_file_label.setText(f"当前文件: {current_file}")

    def on_file_finished(self, index, file_path, result_text, elapsed, confidence_items):
        """Handle single file completion."""
        self.results.append((file_path, result_text, elapsed))

        # Update progress bar
        self.progress_bar.setValue(index + 1)

        # Add to summary
        file_name = file_path.split('/')[-1].split('\\')[-1]
        summary = f"[{index + 1}] {file_name} - {elapsed:.2f}s - {len(result_text)} 字符\n"
        self.results_summary.append(summary)

    def on_batch_error(self, index, file_path, error_msg):
        """Handle batch processing error."""
        file_name = file_path.split('/')[-1].split('\\')[-1]
        error_summary = f"[{index + 1}] {file_name} - 错误: {error_msg}\n"
        self.results_summary.append(error_summary)

    def on_batch_finished(self):
        """Handle batch processing completion."""
        logger.info("[BatchOCR] on_batch_finished called")
        try:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.add_files_btn.setEnabled(True)
            self.clear_files_btn.setEnabled(True)
            self.remove_file_btn.setEnabled(True)

            if self.results:
                self.export_btn.setEnabled(True)
                total_time = sum(r[2] for r in self.results)
                self.status_label.setText(f"处理完成 - 成功 {len(self.results)}/{len(self.file_paths)} 个文件，总耗时 {total_time:.2f} 秒")
            else:
                self.status_label.setText("处理完成 - 没有成功处理的文件")

            self.current_file_label.setText("")
            logger.info("[BatchOCR] UI updated successfully")
        except Exception as e:
            logger.error(f"[BatchOCR] Error in on_batch_finished: {e}", exc_info=True)

    def export_results(self):
        """Export batch results to a text file."""
        from PySide6.QtWidgets import QFileDialog

        if not self.results:
            QMessageBox.warning(self, "警告", "没有可导出的结果")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出结果",
            "batch_ocr_results.txt",
            "文本文件 (*.txt);;所有文件 (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("=" * 60 + "\n")
                    f.write("ScreenOCR 批量处理结果\n")
                    f.write("=" * 60 + "\n\n")

                    for i, (img_path, result_text, elapsed) in enumerate(self.results):
                        f.write(f"--- 文件 {i + 1}: {img_path} ---\n")
                        f.write(f"处理时间: {elapsed:.2f} 秒\n")
                        f.write("识别结果:\n")
                        f.write(result_text)
                        f.write("\n\n" + "=" * 60 + "\n\n")

                QMessageBox.information(self, "成功", f"结果已导出到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出文件失败:\n{str(e)}")

    def closeEvent(self, event):
        """Handle dialog close - cleanup worker."""
        if self._batch_worker:
            self._batch_worker.stop()
            self._batch_worker = None
        super().closeEvent(event)

    def reject(self):
        """Handle dialog reject (ESC or close button) - cleanup worker."""
        if self._batch_worker:
            self._batch_worker.stop()
            self._batch_worker = None
        super().reject()


class SettingsDialog(QDialog):
    """Dialog for application settings."""

    # Signal emitted when settings are changed and need to be applied
    settingsChanged = Signal()

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Setup dialog UI."""
        self.setWindowTitle("设置")
        self.setMinimumSize(450, 400)
        self.resize(520, 620)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Hotkey Section
        hotkey_group = QGroupBox("全局快捷键")
        hotkey_layout = QVBoxLayout(hotkey_group)

        # Current hotkey display
        hotkey_info_layout = QHBoxLayout()
        hotkey_info_layout.addWidget(QLabel("当前截图快捷键:"))
        self.hotkey_label = QLabel("Ctrl+Shift+O")
        self.hotkey_label.setStyleSheet("font-weight: bold; color: #007acc;")
        hotkey_info_layout.addWidget(self.hotkey_label)
        hotkey_info_layout.addStretch()
        hotkey_layout.addLayout(hotkey_info_layout)

        # Configure hotkeys button
        self.configure_hotkeys_btn = QPushButton("配置快捷键...")
        self.configure_hotkeys_btn.clicked.connect(self._open_hotkey_settings)
        self.configure_hotkeys_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)
        hotkey_layout.addWidget(self.configure_hotkeys_btn)

        layout.addWidget(hotkey_group)

        # OCR Model Section
        model_group = QGroupBox("OCR 模型")
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(8)

        model_info_layout = QHBoxLayout()
        model_info_layout.addWidget(QLabel("选择模型:"))
        self.model_combo = QComboBox()
        for key, name in SettingsManager.OCR_MODELS:
            self.model_combo.addItem(name, key)
        self.model_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 200px;
            }
            QComboBox:hover {
                border-color: #007acc;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #d4d4d4;
                selection-background-color: #0e639c;
            }
        """)
        model_info_layout.addWidget(self.model_combo)
        model_info_layout.addStretch()
        model_layout.addLayout(model_info_layout)

        # Model description
        self.model_desc_label = QLabel(
            "PP-OCRv5: 快速识别，适合普通场景\n"
            "PaddleOCR-VL-1.5: 精准识别，适合复杂场景（印章、倾斜、弯曲、复杂光照）"
        )
        self.model_desc_label.setStyleSheet("color: #808080; font-size: 11px;")
        self.model_desc_label.setWordWrap(True)
        model_layout.addWidget(self.model_desc_label)

        layout.addWidget(model_group)

        # Behavior Section
        behavior_group = QGroupBox("行为")
        behavior_layout = QVBoxLayout(behavior_group)
        behavior_layout.setSpacing(8)

        self.auto_copy_check = QPushButton("OCR 完成后自动复制到剪贴板")
        self.auto_copy_check.setCheckable(True)
        self.auto_copy_check.setStyleSheet(self._get_toggle_style())
        behavior_layout.addWidget(self.auto_copy_check)

        self.show_notification_check = QPushButton("OCR 完成后显示通知")
        self.show_notification_check.setCheckable(True)
        self.show_notification_check.setStyleSheet(self._get_toggle_style())
        behavior_layout.addWidget(self.show_notification_check)

        self.minimize_to_tray_check = QPushButton("关闭时最小化到托盘")
        self.minimize_to_tray_check.setCheckable(True)
        self.minimize_to_tray_check.setStyleSheet(self._get_toggle_style())
        behavior_layout.addWidget(self.minimize_to_tray_check)

        layout.addWidget(behavior_group)

        # Document Mode Section
        doc_group = QGroupBox("文档模式 (PP-StructureV3)")
        doc_layout = QVBoxLayout(doc_group)
        doc_layout.setSpacing(8)

        # Document mode options
        self.doc_table_check = QPushButton("表格识别")
        self.doc_table_check.setCheckable(True)
        self.doc_table_check.setStyleSheet(self._get_toggle_style())
        doc_layout.addWidget(self.doc_table_check)

        self.doc_formula_check = QPushButton("公式识别 (LaTeX)")
        self.doc_formula_check.setCheckable(True)
        self.doc_formula_check.setStyleSheet(self._get_toggle_style())
        doc_layout.addWidget(self.doc_formula_check)

        self.doc_seal_check = QPushButton("印章识别")
        self.doc_seal_check.setCheckable(True)
        self.doc_seal_check.setStyleSheet(self._get_toggle_style())
        doc_layout.addWidget(self.doc_seal_check)

        self.doc_chart_check = QPushButton("图表识别")
        self.doc_chart_check.setCheckable(True)
        self.doc_chart_check.setStyleSheet(self._get_toggle_style())
        doc_layout.addWidget(self.doc_chart_check)

        self.doc_orientation_check = QPushButton("文档方向校正")
        self.doc_orientation_check.setCheckable(True)
        self.doc_orientation_check.setStyleSheet(self._get_toggle_style())
        doc_layout.addWidget(self.doc_orientation_check)

        self.doc_unwarping_check = QPushButton("文档弯曲矫正")
        self.doc_unwarping_check.setCheckable(True)
        self.doc_unwarping_check.setStyleSheet(self._get_toggle_style())
        doc_layout.addWidget(self.doc_unwarping_check)

        # Info label
        doc_info_label = QLabel("启用更多功能会增加加载时间")
        doc_info_label.setStyleSheet("color: #808080; font-size: 11px;")
        doc_layout.addWidget(doc_info_label)

        layout.addWidget(doc_group)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()

        self.reset_btn = QPushButton("恢复默认设置")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(self.reset_btn)

        button_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

    def _get_toggle_style(self):
        """Get stylesheet for toggle buttons."""
        return """
            QPushButton {
                text-align: left;
                padding: 8px 12px;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                background-color: #2d2d2d;
                color: #d4d4d4;
                font-size: 13px;
                min-height: 28px;
                max-height: 32px;
            }
            QPushButton:checked {
                background-color: #0e639c;
                border-color: #007acc;
                color: #ffffff;
            }
            QPushButton:hover {
                border-color: #007acc;
            }
        """

    def load_settings(self):
        """Load current settings into UI."""
        settings = self.settings_manager.settings

        # Hotkey - update display label
        hotkey = settings.hotkey
        self.hotkey_label.setText(self.settings_manager.get_hotkey_display_name(hotkey))

        # OCR Model
        model_index = self.model_combo.findData(settings.ocr_model)
        if model_index >= 0:
            self.model_combo.setCurrentIndex(model_index)

        # Behavior
        self.auto_copy_check.setChecked(settings.auto_copy)
        self.show_notification_check.setChecked(settings.show_notification)
        self.minimize_to_tray_check.setChecked(settings.minimize_to_tray)

        # Document Mode
        self.doc_table_check.setChecked(settings.doc_use_table_recognition)
        self.doc_formula_check.setChecked(settings.doc_use_formula_recognition)
        self.doc_seal_check.setChecked(settings.doc_use_seal_recognition)
        self.doc_chart_check.setChecked(settings.doc_use_chart_recognition)
        self.doc_orientation_check.setChecked(settings.doc_use_doc_orientation)
        self.doc_unwarping_check.setChecked(settings.doc_use_doc_unwarping)

    def _open_hotkey_settings(self):
        """Open the advanced hotkey settings dialog."""
        from hotkey_settings_dialog import HotkeySettingsDialog
        dialog = HotkeySettingsDialog(self.settings_manager, self)
        dialog.hotkeys_changed.connect(self._on_hotkeys_changed)
        dialog.exec()

    def _on_hotkeys_changed(self, new_hotkeys):
        """Handle hotkey changes from the advanced dialog."""
        # Update the display label
        hotkey = self.settings_manager.get('hotkey', 'ctrl+shift+o')
        self.hotkey_label.setText(self.settings_manager.get_hotkey_display_name(hotkey))
        # Emit signal to notify main window to update global hotkeys
        self.settingsChanged.emit()

    def save_settings(self):
        """Save settings and close dialog."""
        settings = self.settings_manager.settings

        # OCR Model
        settings.ocr_model = self.model_combo.currentData()

        # Behavior
        settings.auto_copy = self.auto_copy_check.isChecked()
        settings.show_notification = self.show_notification_check.isChecked()
        settings.minimize_to_tray = self.minimize_to_tray_check.isChecked()

        # Document Mode
        settings.doc_use_table_recognition = self.doc_table_check.isChecked()
        settings.doc_use_formula_recognition = self.doc_formula_check.isChecked()
        settings.doc_use_seal_recognition = self.doc_seal_check.isChecked()
        settings.doc_use_chart_recognition = self.doc_chart_check.isChecked()
        settings.doc_use_doc_orientation = self.doc_orientation_check.isChecked()
        settings.doc_use_doc_unwarping = self.doc_unwarping_check.isChecked()

        # Save to file
        self.settings_manager.save()

        # Emit signal to notify main window
        self.settingsChanged.emit()

        self.accept()

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要恢复所有默认设置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.reset_to_defaults()
            self.load_settings()


class MainWindow(QMainWindow):
    """Main application window."""

    # Signals
    settings_changed = Signal()  # Emitted when settings are changed

    def __init__(self):
        super().__init__()
        self.ocr_engine = None
        self._ocr_thread = None
        self._ocr_worker = None
        self._doc_worker = None
        self._temp_image_path = None
        self._current_pixmap = None  # Store current screenshot for history
        self.history_manager = HistoryManager()
        self.settings_manager = SettingsManager()
        self._ocr_initializing = False  # Flag to prevent concurrent initialization
        self._ocr_mode = "text"  # "text" or "document"
        self.vision_server = None  # [Task 687] Vision server instance
        self.setup_ui()
        # OCR engine is now lazily initialized on first use
        self._lazy_init_ocr = True
        self.setup_device_combo()
        # [Task 687] Start vision server for self-testing
        self._start_vision_server()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("ScreenOCR - Desktop OCR Tool")
        self.setMinimumSize(900, 600)
        self.resize(1200, 800)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Toolbar
        self.setup_toolbar()

        # Main content area with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3e3e3e;
                border-radius: 2px;
            }
            QSplitter::handle:hover {
                background-color: #007acc;
            }
        """)

        # Left: Image preview
        self.preview_widget = ImagePreviewWidget()
        splitter.addWidget(self.preview_widget)

        # Right: OCR result (stacked widget for different modes)
        from PySide6.QtWidgets import QStackedWidget
        self.result_stack = QStackedWidget()

        # Text mode widget
        self.result_widget = ResultTextWidget()
        self.result_widget.copyRequested.connect(self.copy_result)
        self.result_widget.saveRequested.connect(self.save_result_to_file)
        self.result_stack.addWidget(self.result_widget)

        # Document mode widget
        self.document_widget = DocumentResultWidget()
        self.document_widget.copyRequested.connect(self.copy_markdown)
        self.document_widget.exportMarkdownRequested.connect(self.export_markdown)
        self.result_stack.addWidget(self.document_widget)

        splitter.addWidget(self.result_stack)

        # Set stretch factors for proportional resizing (1:1 ratio)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # Set initial sizes (50% preview, 50% result)
        splitter.setSizes([500, 500])

        main_layout.addWidget(splitter, 1)  # Add stretch factor to fill space

        # Status bar
        self.setup_statusbar()

    def setup_toolbar(self):
        """Setup the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setStyleSheet("""
            QToolBar {
                spacing: 8px;
                padding: 6px 12px;
            }
            QToolButton {
                padding: 6px 16px;
            }
            QComboBox {
                padding: 4px 8px;
            }
        """)
        self.addToolBar(toolbar)

        # Left group: Screenshot and Open
        self.action_screenshot = QAction("截图 (Ctrl+Shift+O)", self)
        self.action_screenshot.setShortcut("Ctrl+Shift+O")
        self.action_screenshot.triggered.connect(self.start_screenshot)
        toolbar.addAction(self.action_screenshot)

        self.action_open = QAction("打开图片", self)
        self.action_open.triggered.connect(self.open_image)
        toolbar.addAction(self.action_open)

        toolbar.addSeparator()

        # Mode switch buttons
        self.text_mode_btn = QPushButton("文字模式")
        self.text_mode_btn.setCheckable(True)
        self.text_mode_btn.setChecked(True)
        self.text_mode_btn.setFixedWidth(90)
        self.text_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: #ffffff;
                border: 1px solid #1177bb;
                border-radius: 3px;
                padding: 4px 12px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #0e639c;
                border-color: #1177bb;
            }
            QPushButton:!checked {
                background-color: #3c3c3c;
                border-color: #555555;
                font-weight: normal;
            }
            QPushButton:hover {
                border-color: #007acc;
            }
        """)
        self.text_mode_btn.clicked.connect(lambda: self._set_ocr_mode("text"))
        toolbar.addWidget(self.text_mode_btn)

        self.doc_mode_btn = QPushButton("文档模式")
        self.doc_mode_btn.setCheckable(True)
        self.doc_mode_btn.setFixedWidth(90)
        self.doc_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 4px 12px;
                font-size: 13px;
            }
            QPushButton:checked {
                background-color: #0e639c;
                border-color: #1177bb;
                font-weight: bold;
            }
            QPushButton:hover {
                border-color: #007acc;
            }
        """)
        self.doc_mode_btn.clicked.connect(lambda: self._set_ocr_mode("document"))
        toolbar.addWidget(self.doc_mode_btn)

        toolbar.addSeparator()

        # Right group: History, Batch, and Settings
        self.action_history = QAction("历史记录", self)
        self.action_history.triggered.connect(self.show_history)
        toolbar.addAction(self.action_history)

        self.action_batch = QAction("批量处理", self)
        self.action_batch.triggered.connect(self.show_batch_dialog)
        toolbar.addAction(self.action_batch)

        self.action_settings = QAction("设置", self)
        self.action_settings.triggered.connect(self.show_settings)
        toolbar.addAction(self.action_settings)

    def setup_statusbar(self):
        """Setup the status bar with aligned information."""
        self.statusbar = QStatusBar()
        self.statusbar.setSizeGripEnabled(False)  # Hide the resize grip
        self.statusbar.setStyleSheet("""
            QStatusBar {
                background-color: #007acc;
                color: #ffffff;
                padding: 4px 12px;
            }
            QStatusBar::item {
                border: none;
            }
            QLabel {
                color: #ffffff;
                padding: 0 8px;
            }
        """)
        self.setStatusBar(self.statusbar)

        # Left: Status
        self.time_label = QLabel("就绪")
        self.time_label.setStyleSheet("font-weight: bold;")
        self.statusbar.addWidget(self.time_label)

        # Right: Version info (permanent widget stays on right)
        version_label = QLabel("ScreenOCR v1.0.0")
        version_label.setStyleSheet("color: rgba(255,255,255,0.8);")
        self.statusbar.addPermanentWidget(version_label)

    def setup_device_combo(self):
        """Setup device - now always uses CPU."""
        # Always use CPU, no device selection needed
        self.time_label.setText("就绪 - OCR引擎将在首次使用时初始化")

    def _start_vision_server(self):
        """[Task 687] Start the vision server for self-testing."""
        try:
            from vision_server import create_vision_server
            import asyncio

            self.vision_server = create_vision_server(self)

            # Start server in background using QTimer
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._run_vision_server)

            logger.info("[MainWindow] Vision server scheduled to start")
        except Exception as e:
            logger.warning(f"[MainWindow] Failed to start vision server: {e}")

    def _run_vision_server(self):
        """[Task 687] Run vision server async loop in background."""
        import asyncio
        import threading

        def run_server():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.vision_server.start())
                loop.run_forever()
            except Exception as e:
                logger.error(f"[VisionServer] Server error: {e}")

        # Run in daemon thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        logger.info("[MainWindow] Vision server started on ws://127.0.0.1:18900")

    def _stop_vision_server(self):
        """[Task 687] Stop the vision server."""
        if self.vision_server:
            try:
                import asyncio
                asyncio.create_task(self.vision_server.stop())
                logger.info("[MainWindow] Vision server stopped")
            except Exception as e:
                logger.warning(f"[MainWindow] Error stopping vision server: {e}")

    # [Task 687] Vision server action handlers
    def on_screenshot(self):
        """Handler for screenshot action."""
        self.start_screenshot()

    def on_document_analysis(self):
        """Handler for document analysis action."""
        self._set_ocr_mode("document")
        self.start_screenshot()

    def on_batch_process(self):
        """Handler for batch process action."""
        self.show_batch_dialog()

    def on_show_history(self):
        """Handler for show history action."""
        self.show_history()

    def on_settings(self):
        """Handler for settings action."""
        self.show_settings()

    def on_clear_result(self):
        """Handler for clear result action."""
        self.result_widget.clear()
        self.preview_widget.clear()

    def on_copy_result(self):
        """Handler for copy result action."""
        self.copy_result()

    def on_save_result(self):
        """Handler for save result action."""
        self.save_result_to_file()

    def ensure_ocr_engine(self):
        """Ensure OCR engine is initialized (lazy loading)."""
        settings = self.settings_manager.settings

        # Check if engine exists and language matches
        if (self.ocr_engine is not None and
            self.ocr_engine._initialized and
            self.ocr_engine._lang == settings.ocr_language):
            return True

        # If engine exists but language changed, cleanup old engine
        if self.ocr_engine is not None:
            self.ocr_engine.cleanup()
            self.ocr_engine = None

        if self._ocr_initializing:
            # Already initializing, wait for it
            return False

        self._ocr_initializing = True
        self.time_label.setText("正在初始化 OCR 引擎...")
        self.statusbar.repaint()

        try:
            # Always use CPU
            device_id = 'cpu'

            self.ocr_engine = OCREngine(
                device_id=device_id,
                lang=settings.ocr_language,
                model_type=settings.ocr_model
            )

            # Get version info
            version_info = self.ocr_engine.get_version_info()
            model_type = self.ocr_engine.get_model_display_name()
            version_text = ""
            if version_info['is_v3_or_higher']:
                version_text = f" (PaddleOCR 3.0 + {model_type})"
            else:
                version_text = f" (PaddleOCR {version_info.get('paddleocr_version', '2.x')} + {model_type})"

            # Update status
            self.time_label.setText(f"OCR 引擎已就绪{version_text}")
            return True

        except Exception as e:
            self.time_label.setText(f"OCR 引擎初始化失败: {e}")
            QMessageBox.critical(
                self,
                "初始化错误",
                f"OCR 引擎初始化失败:\n{str(e)}\n\n请检查 PaddleOCR 是否正确安装。"
            )
            return False
        finally:
            self._ocr_initializing = False

    def setup_ocr_engine(self):
        """Initialize the OCR engine (deprecated, use ensure_ocr_engine)."""
        return self.ensure_ocr_engine()

    def _set_ocr_mode(self, mode: str):
        """Switch between text and document OCR mode."""
        if mode == self._ocr_mode:
            return

        self._ocr_mode = mode

        if mode == "text":
            self.text_mode_btn.setChecked(True)
            self.doc_mode_btn.setChecked(False)
            self.result_stack.setCurrentIndex(0)
            self.time_label.setText("已切换到文字模式")
        else:  # document mode
            self.text_mode_btn.setChecked(False)
            self.doc_mode_btn.setChecked(True)
            self.result_stack.setCurrentIndex(1)
            self.time_label.setText("已切换到文档模式 (PP-StructureV3)")

    def _run_document_analysis_async(self, image_path):
        """Run document structure analysis in background thread to avoid UI freeze.

        [Task 763] Changed to use QThread for background document analysis.
        """
        # Cleanup previous worker if exists
        self._cleanup_ocr_thread()

        # Disable UI during processing
        self.action_screenshot.setEnabled(False)
        self.action_open.setEnabled(False)
        self.time_label.setText("文档分析中...")
        self.statusbar.repaint()

        # Get document settings from settings manager
        settings = self.settings_manager.settings
        doc_settings = {
            'use_table_recognition': settings.doc_use_table_recognition,
            'use_formula_recognition': settings.doc_use_formula_recognition,
            'use_seal_recognition': settings.doc_use_seal_recognition,
            'use_chart_recognition': settings.doc_use_chart_recognition,
            'use_doc_orientation': settings.doc_use_doc_orientation,
            'use_doc_unwarping': settings.doc_use_doc_unwarping,
        }

        # Create thread and worker
        self._ocr_thread = QThread()
        self._doc_worker = DocumentOCRWorker(self.ocr_engine, image_path, doc_settings)
        self._doc_worker.moveToThread(self._ocr_thread)

        # Connect signals
        self._ocr_thread.started.connect(self._doc_worker.run)
        self._doc_worker.finished.connect(self._on_document_analysis_finished)
        self._doc_worker.finished.connect(self._ocr_thread.quit)
        self._doc_worker.error.connect(self._on_document_analysis_error)
        self._doc_worker.error.connect(self._ocr_thread.quit)

        # Start the thread
        self._ocr_thread.start()

    def _on_document_analysis_finished(self, result: str, elapsed: float):
        """Handle document analysis completion."""
        # Display result in document widget (markdown string)
        self.document_widget.set_markdown(result)

        self.time_label.setText(f"文档分析完成，耗时 {elapsed:.2f} 秒")

        # Save to history (use markdown as text)
        if result.strip():
            self.history_manager.add_record(
                text=result,
                image=self._current_pixmap,
                elapsed_time=elapsed
            )

        # Re-enable UI
        self._enable_ui()

        # Cleanup temp file
        self._cleanup_temp_file()

    def _on_document_analysis_error(self, error_msg: str):
        """Handle document analysis error."""
        QMessageBox.critical(
            self,
            "错误",
            f"文档分析失败:\n{error_msg}"
        )
        self.time_label.setText("错误")

        # Re-enable UI
        self._enable_ui()

        # Cleanup temp file
        self._cleanup_temp_file()

    def copy_markdown(self):
        """Copy markdown result to clipboard."""
        from PySide6.QtWidgets import QApplication

        text = self.document_widget.get_markdown()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.time_label.setText("Markdown 已复制到剪贴板！")

    def export_markdown(self):
        """Export markdown result to file."""
        from PySide6.QtWidgets import QFileDialog

        text = self.document_widget.get_markdown()
        if not text:
            QMessageBox.warning(self, "警告", "没有可导出的 Markdown 内容")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 Markdown",
            "document_result.md",
            "Markdown 文件 (*.md);;所有文件 (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                self.time_label.setText(f"Markdown 已导出到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出文件失败:\n{str(e)}")

    def start_screenshot(self):
        """Start screenshot capture."""
        # Create overlay only once, reuse it
        if not hasattr(self, '_screenshot_overlay') or self._screenshot_overlay is None:
            self._screenshot_overlay = ScreenshotOverlay()
            # Connect signals only once when creating
            self._screenshot_overlay.captured.connect(self._on_screenshot_captured)
            self._screenshot_overlay.cancelled.connect(self._on_screenshot_cancelled)

        # Hide main window during capture
        self.hide()

        # Start overlay after a short delay to ensure window is hidden
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._screenshot_overlay.start)

    def _on_screenshot_captured(self, pixmap):
        """Handle captured screenshot."""
        # Show main window
        self.show()
        self.activateWindow()

        # Store pixmap for history
        self._current_pixmap = pixmap

        # Display captured image
        self.preview_widget.set_image(pixmap)

        # Process with OCR
        self._process_pixmap(pixmap)

    def _on_screenshot_cancelled(self):
        """Handle screenshot cancelled."""
        self.show()
        self.activateWindow()

    def _process_pixmap(self, pixmap):
        """Process a QPixmap with OCR (async)."""
        import tempfile
        import os

        try:
            # Ensure OCR engine is initialized first
            if not self.ensure_ocr_engine():
                if self._ocr_initializing:
                    self.time_label.setText("等待 OCR 引擎初始化...")
                    # Retry after a short delay
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(500, lambda: self._process_pixmap(pixmap))
                    return
                else:
                    QMessageBox.critical(
                        self,
                        "错误",
                        "OCR 引擎初始化失败，无法处理图片。"
                    )
                    return

            # Save pixmap to temp file for OCR
            temp_dir = tempfile.gettempdir()
            self._temp_image_path = os.path.join(temp_dir, "screenocr_temp.png")
            pixmap.save(self._temp_image_path, "PNG")

            # Run OCR or document analysis based on current mode
            if self._ocr_mode == "document":
                self._run_document_analysis_async(self._temp_image_path)
            else:
                self._run_ocr_async(self._temp_image_path)

        except Exception as e:
            QMessageBox.critical(
                self,
                "错误",
                f"处理截图失败:\n{str(e)}"
            )
            self.time_label.setText("错误")

    def _run_ocr_async(self, image_path):
        """Run OCR in background thread to avoid UI freeze.

        [Task 763] Changed to use QThread for background OCR processing.
        """
        # Cleanup previous worker if exists
        self._cleanup_ocr_thread()

        # Disable UI during OCR
        self.action_screenshot.setEnabled(False)
        self.action_open.setEnabled(False)
        self.time_label.setText("处理中...")
        self.statusbar.repaint()

        # Create thread and worker
        self._ocr_thread = QThread()
        self._ocr_worker = OCRWorker(self.ocr_engine, image_path)
        self._ocr_worker.moveToThread(self._ocr_thread)

        # Connect signals
        self._ocr_thread.started.connect(self._ocr_worker.run)
        self._ocr_worker.finished.connect(self._on_ocr_finished)
        self._ocr_worker.finished.connect(self._ocr_thread.quit)
        self._ocr_worker.error.connect(self._on_ocr_error)
        self._ocr_worker.error.connect(self._ocr_thread.quit)

        # Start the thread
        self._ocr_thread.start()

    def _on_ocr_finished(self, result_text, elapsed, confidence_items):
        """Handle OCR completion."""
        # Store confidence items
        self.result_widget.set_confidence_items(confidence_items)

        self.time_label.setText(f"OCR 完成，耗时 {elapsed:.2f} 秒")

        # Save to history
        if result_text.strip():
            self.history_manager.add_record(
                text=result_text,
                image=self._current_pixmap,
                elapsed_time=elapsed
            )

        # Re-enable UI
        self._enable_ui()

        # Cleanup temp file
        self._cleanup_temp_file()

    def _on_ocr_error(self, error_msg):
        """Handle OCR error."""
        QMessageBox.critical(
            self,
            "错误",
            f"OCR 失败:\n{error_msg}"
        )
        self.time_label.setText("错误")

        # Re-enable UI
        self._enable_ui()

        # Cleanup temp file
        self._cleanup_temp_file()

    def _enable_ui(self):
        """Re-enable UI after OCR."""
        self.action_screenshot.setEnabled(True)
        self.action_open.setEnabled(True)

    def _cleanup_ocr_thread(self):
        """Cleanup OCR thread and worker resources.

        [Task 763] Updated to properly cleanup QThread instances.
        """
        if self._ocr_thread is not None:
            if self._ocr_thread.isRunning():
                self._ocr_thread.quit()
                self._ocr_thread.wait(3000)  # Wait up to 3 seconds
            self._ocr_thread = None
        self._ocr_worker = None
        self._doc_worker = None

    def _cleanup_temp_file(self):
        """Cleanup temporary image file."""
        import os
        if self._temp_image_path and os.path.exists(self._temp_image_path):
            try:
                os.remove(self._temp_image_path)
            except Exception:
                pass
            self._temp_image_path = None

    def open_image(self):
        """Open an image file for OCR."""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开图片",
            "",
            "图片 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*)"
        )

        if file_path:
            self.process_image(file_path)

    def process_image(self, image_path):
        """Process an image with OCR (async)."""
        from PIL import Image

        try:
            # Ensure OCR engine is initialized first
            if not self.ensure_ocr_engine():
                if self._ocr_initializing:
                    self.time_label.setText("等待 OCR 引擎初始化...")
                    # Retry after a short delay
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(500, lambda: self.process_image(image_path))
                    return
                else:
                    QMessageBox.critical(
                        self,
                        "错误",
                        "OCR 引擎初始化失败，无法处理图片。"
                    )
                    return

            # Load and display image
            image = Image.open(image_path)
            self.preview_widget.set_image(image)

            # Run OCR or document analysis based on current mode
            if self._ocr_mode == "document":
                self._run_document_analysis_async(image_path)
            else:
                self._run_ocr_async(image_path)

        except Exception as e:
            QMessageBox.critical(
                self,
                "错误",
                f"处理图片失败:\n{str(e)}"
            )
            self.time_label.setText("错误")

    def copy_result(self):
        """Copy OCR result to clipboard."""
        from PySide6.QtWidgets import QApplication

        text = self.result_widget.get_text()

        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.time_label.setText("已复制到剪贴板！")

    def save_result_to_file(self):
        """Save OCR result to text file."""
        success, result = self.result_widget.save_to_file()
        if success:
            self.time_label.setText(f"已保存到: {result}")
        elif result:
            QMessageBox.critical(self, "保存失败", f"保存文件失败:\n{result}")

    def show_history(self):
        """Show history dialog."""
        dialog = HistoryDialog(self.history_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # User selected a record to restore
            record = dialog.selected_record
            if record:
                self.result_widget.set_text(record.text)
                self.time_label.setText(f"从历史记录恢复 ({record.timestamp})")

    def show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self.settings_manager, self)
        dialog.settingsChanged.connect(self._on_settings_changed)
        dialog.exec()

    def show_batch_dialog(self):
        """Show batch OCR dialog."""
        # Ensure OCR engine is initialized first
        if not self.ensure_ocr_engine():
            if self._ocr_initializing:
                self.time_label.setText("等待 OCR 引擎初始化...")
                # Retry after a short delay
                from PySide6.QtCore import QTimer
                QTimer.singleShot(500, self.show_batch_dialog)
                return
            else:
                QMessageBox.critical(
                    self,
                    "错误",
                    "OCR 引擎初始化失败，无法使用批量处理功能。"
                )
                return

        dialog = BatchOCRDialog(self.ocr_engine, self)
        dialog.exec()

    def _on_settings_changed(self):
        """Handle settings changed - reload OCR engine if language or model changed."""
        settings = self.settings_manager.settings
        # Update OCR engine settings if engine exists
        if self.ocr_engine:
            old_lang = self.ocr_engine._lang
            old_model = self.ocr_engine._model_type
            self.ocr_engine.set_language(settings.ocr_language)
            self.ocr_engine.set_model_type(settings.ocr_model)

            changes = []
            if old_lang != settings.ocr_language:
                changes.append(f"语言: {old_lang} -> {settings.ocr_language}")
            if old_model != settings.ocr_model:
                changes.append(f"模型: {old_model} -> {settings.ocr_model}")

            if changes:
                self.time_label.setText(f"已更改: {', '.join(changes)}，OCR引擎将在下次使用时重新初始化")
            else:
                self.time_label.setText("设置已保存")
        else:
            self.time_label.setText("设置已保存 - OCR引擎将在首次使用时初始化")

    def closeEvent(self, event):
        """Handle window close event - minimize to tray instead of quitting."""
        # Hide to tray instead of closing
        event.ignore()
        self.hide()

    def force_close(self):
        """Force close the window and cleanup resources."""
        # Cleanup OCR thread
        self._cleanup_ocr_thread()
        self._cleanup_temp_file()
        # Cleanup OCR engine
        if self.ocr_engine:
            self.ocr_engine.cleanup()
        # [Task 687] Stop vision server
        self._stop_vision_server()
