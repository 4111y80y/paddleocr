#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ScreenOCR - Screenshot Overlay
Full-screen overlay for selecting screen region to capture.
"""

from PySide6.QtWidgets import QWidget, QApplication, QLabel
from PySide6.QtCore import Qt, QRect, QPoint, Signal, QSize
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPixmap,
    QCursor, QGuiApplication, QScreen, QFont
)


class ScreenshotOverlay(QWidget):
    """
    Full-screen overlay widget for capturing screen regions.

    Features:
    - Semi-transparent dark overlay
    - Mouse drag to select region
    - Real-time display of selection size
    - Press Esc to cancel
    - Returns the captured region as QPixmap
    - Magnifier: shows zoomed view near cursor
    - Coordinates: displays current cursor position
    - Arrow keys: fine-tune selection by 1 pixel
    """

    # Signal emitted when screenshot is captured (QPixmap)
    captured = Signal(QPixmap)
    # Signal emitted when capture is cancelled
    cancelled = Signal()

    # Constants for magnifier
    MAGNIFIER_SIZE = 120
    MAGNIFIER_ZOOM = 2.0
    MAGNIFIER_OFFSET = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._reset_state()

    def _setup_ui(self):
        """Setup the overlay UI."""
        # Frameless, stay on top, cover entire screen
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Size label for showing selection dimensions
        self.size_label = QLabel(self)
        self.size_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 120, 215, 200);
                color: white;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.size_label.hide()

        # Coordinate label for showing cursor position
        self.coord_label = QLabel(self)
        self.coord_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 11px;
                font-family: Consolas, monospace;
            }
        """)
        self.coord_label.hide()

        # Hint label
        self.hint_label = QLabel("拖拽选择区域，按 Esc 取消 | 方向键微调选区", self)
        self.hint_label.setStyleSheet("""
            QLabel {
                background-color: rgba(50, 50, 50, 180);
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
        """)

    def _reset_state(self):
        """Reset selection state."""
        self._is_selecting = False
        self._start_point = QPoint()
        self._end_point = QPoint()
        self._selection_rect = QRect()
        self._screen_pixmap = None
        self._current_cursor_pos = QPoint()

    def start(self):
        """Start the screenshot capture process."""
        self._reset_state()

        # Capture the entire screen first
        self._capture_screen()

        # Show fullscreen
        self.showFullScreen()

        # Center hint label
        self._update_hint_position()
        self.hint_label.show()

        # Grab keyboard focus (critical for receiving key events)
        self.activateWindow()
        self.setFocus()
        self.grabKeyboard()

    def _capture_screen(self):
        """Capture the entire screen as background."""
        # Get the primary screen
        screen = QGuiApplication.primaryScreen()
        if screen:
            # Capture entire screen
            geometry = screen.geometry()
            self._screen_pixmap = screen.grabWindow(
                0,  # Window ID 0 = entire screen
                geometry.x(),
                geometry.y(),
                geometry.width(),
                geometry.height()
            )
            self.setGeometry(geometry)

    def _update_hint_position(self):
        """Update hint label position to center of screen."""
        if self._screen_pixmap:
            x = (self.width() - self.hint_label.width()) // 2
            y = 50  # Near top
            self.hint_label.move(x, y)
            self.hint_label.adjustSize()

    def paintEvent(self, event):
        """Paint the overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the captured screen as background
        if self._screen_pixmap:
            painter.drawPixmap(0, 0, self._screen_pixmap)

        # Draw semi-transparent overlay
        overlay_color = QColor(0, 0, 0, 120)

        if self._selection_rect.isValid() and not self._selection_rect.isEmpty():
            # Draw overlay around selection (4 rectangles)
            rect = self._selection_rect.normalized()

            # Top region
            painter.fillRect(
                0, 0,
                self.width(), rect.top(),
                overlay_color
            )
            # Bottom region
            painter.fillRect(
                0, rect.bottom() + 1,
                self.width(), self.height() - rect.bottom() - 1,
                overlay_color
            )
            # Left region
            painter.fillRect(
                0, rect.top(),
                rect.left(), rect.height(),
                overlay_color
            )
            # Right region
            painter.fillRect(
                rect.right() + 1, rect.top(),
                self.width() - rect.right() - 1, rect.height(),
                overlay_color
            )

            # Draw selection border
            pen = QPen(QColor(0, 120, 215), 2)
            painter.setPen(pen)
            painter.drawRect(rect)

            # Draw corner handles
            handle_size = 8
            handle_color = QColor(0, 120, 215)
            painter.setBrush(QBrush(handle_color))
            painter.setPen(Qt.PenStyle.NoPen)

            corners = [
                rect.topLeft(),
                rect.topRight(),
                rect.bottomLeft(),
                rect.bottomRight()
            ]
            for corner in corners:
                painter.drawRect(
                    corner.x() - handle_size // 2,
                    corner.y() - handle_size // 2,
                    handle_size,
                    handle_size
                )
        else:
            # No selection - draw full overlay
            painter.fillRect(self.rect(), overlay_color)

        # Draw magnifier at cursor position
        self._draw_magnifier(painter)

    def _draw_magnifier(self, painter):
        """Draw magnifier showing zoomed view at cursor position."""
        if not self._screen_pixmap or self._current_cursor_pos.isNull():
            return

        cursor_pos = self._current_cursor_pos
        mag_size = self.MAGNIFIER_SIZE
        zoom = self.MAGNIFIER_ZOOM
        offset = self.MAGNIFIER_OFFSET

        # Calculate magnifier position (avoid going off-screen)
        mag_x = cursor_pos.x() + offset
        mag_y = cursor_pos.y() + offset

        # Adjust if going off right edge
        if mag_x + mag_size > self.width():
            mag_x = cursor_pos.x() - mag_size - offset

        # Adjust if going off bottom edge
        if mag_y + mag_size > self.height():
            mag_y = cursor_pos.y() - mag_size - offset

        # Ensure within bounds
        mag_x = max(10, min(mag_x, self.width() - mag_size - 10))
        mag_y = max(10, min(mag_y, self.height() - mag_size - 10))

        # Calculate source rect (area around cursor to zoom)
        src_size = int(mag_size / zoom)
        src_x = cursor_pos.x() - src_size // 2
        src_y = cursor_pos.y() - src_size // 2

        # Clamp source rect to pixmap bounds
        src_x = max(0, min(src_x, self._screen_pixmap.width() - src_size))
        src_y = max(0, min(src_y, self._screen_pixmap.height() - src_size))

        # Create magnifier pixmap
        mag_pixmap = QPixmap(mag_size, mag_size)
        mag_pixmap.fill(Qt.GlobalColor.black)

        mag_painter = QPainter(mag_pixmap)
        mag_painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Draw zoomed portion
        source_rect = QRect(src_x, src_y, src_size, src_size)
        target_rect = QRect(0, 0, mag_size, mag_size)
        mag_painter.drawPixmap(target_rect, self._screen_pixmap, source_rect)

        # Draw crosshair in magnifier
        mag_painter.setPen(QPen(QColor(255, 0, 0), 1))
        center = mag_size // 2
        mag_painter.drawLine(center, 0, center, mag_size)
        mag_painter.drawLine(0, center, mag_size, center)

        mag_painter.end()

        # Draw magnifier background and border
        painter.setBrush(QBrush(QColor(40, 40, 40)))
        painter.setPen(QPen(QColor(0, 120, 215), 2))
        painter.drawRoundedRect(mag_x - 2, mag_y - 2, mag_size + 4, mag_size + 4, 6, 6)

        # Draw the magnifier pixmap
        painter.drawPixmap(mag_x, mag_y, mag_pixmap)

        # Draw cursor position info
        info_text = f"({cursor_pos.x()}, {cursor_pos.y()})"
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Consolas", 9))
        text_rect = painter.boundingRect(mag_x, mag_y + mag_size + 5, mag_size, 20, Qt.AlignmentFlag.AlignCenter, info_text)
        painter.fillRect(text_rect.adjusted(-4, -2, 4, 2), QColor(0, 0, 0, 180))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, info_text)

    def mousePressEvent(self, event):
        """Handle mouse press - start selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_selecting = True
            self._start_point = event.pos()
            self._end_point = event.pos()
            self._selection_rect = QRect(self._start_point, self._end_point)
            self.hint_label.hide()
            self.update()

    def mouseMoveEvent(self, event):
        """Handle mouse move - update selection."""
        # Update current cursor position for magnifier
        self._current_cursor_pos = event.pos()

        # Update coordinate label
        self.coord_label.setText(f"{self._current_cursor_pos.x()}, {self._current_cursor_pos.y()}")
        self.coord_label.adjustSize()

        # Position coordinate label near cursor but not overlapping
        coord_x = self._current_cursor_pos.x() + 15
        coord_y = self._current_cursor_pos.y() - self.coord_label.height() - 10

        # Keep on screen
        if coord_x + self.coord_label.width() > self.width():
            coord_x = self._current_cursor_pos.x() - self.coord_label.width() - 15
        if coord_y < 0:
            coord_y = self._current_cursor_pos.y() + 20

        self.coord_label.move(coord_x, coord_y)
        self.coord_label.show()

        if self._is_selecting:
            self._end_point = event.pos()
            self._selection_rect = QRect(self._start_point, self._end_point).normalized()

            # Update size label
            w = self._selection_rect.width()
            h = self._selection_rect.height()
            self.size_label.setText(f"{w} x {h}")
            self.size_label.adjustSize()

            # Position size label near selection
            label_x = self._selection_rect.right() - self.size_label.width()
            label_y = self._selection_rect.bottom() + 5

            # Keep label on screen
            if label_y + self.size_label.height() > self.height():
                label_y = self._selection_rect.top() - self.size_label.height() - 5
            if label_x < 0:
                label_x = self._selection_rect.left()

            self.size_label.move(label_x, label_y)
            self.size_label.show()

        self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release - finish selection."""
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            self._end_point = event.pos()
            self._selection_rect = QRect(self._start_point, self._end_point).normalized()

            # Check if selection is valid (minimum size)
            if self._selection_rect.width() > 10 and self._selection_rect.height() > 10:
                self._capture_selection()
            else:
                # Selection too small, reset
                self._selection_rect = QRect()
                self.size_label.hide()
                self.hint_label.show()
                self._update_hint_position()
                self.update()

    def _capture_selection(self):
        """Capture the selected region and emit signal."""
        if self._screen_pixmap and self._selection_rect.isValid():
            # Extract the selected region from captured screen
            captured = self._screen_pixmap.copy(self._selection_rect)

            # Hide overlay first
            self.hide()

            # Emit captured signal
            self.captured.emit(captured)

    def keyPressEvent(self, event):
        """Handle key press - Esc to cancel, arrow keys to fine-tune selection."""
        if event.key() == Qt.Key.Key_Escape:
            # Reset selection state to prevent mouseReleaseEvent from capturing
            self._is_selecting = False
            self._selection_rect = QRect()
            # Hide all labels
            self.size_label.hide()
            self.coord_label.hide()
            self.hide()
            self.cancelled.emit()
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            # Fine-tune selection with arrow keys
            self._fine_tune_selection(event.key())
        else:
            super().keyPressEvent(event)

    def _fine_tune_selection(self, key):
        """Fine-tune selection rectangle by 1 pixel using arrow keys."""
        if not self._selection_rect.isValid() or self._selection_rect.isEmpty():
            return

        # Determine adjustment amount
        dx = 0
        dy = 0
        shift_modifier = QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
        step = 10 if shift_modifier else 1  # Shift + arrow = 10 pixels

        if key == Qt.Key.Key_Left:
            dx = -step
        elif key == Qt.Key.Key_Right:
            dx = step
        elif key == Qt.Key.Key_Up:
            dy = -step
        elif key == Qt.Key.Key_Down:
            dy = step

        # Adjust selection rectangle
        rect = self._selection_rect.normalized()
        new_rect = QRect(rect)

        # If currently selecting (dragging), adjust end point
        # Otherwise adjust the entire selection
        if self._is_selecting:
            new_rect = QRect(rect.topLeft(), rect.bottomRight() + QPoint(dx, dy))
        else:
            # Move entire selection
            new_rect = rect.translated(dx, dy)

        # Ensure selection stays within screen bounds
        if new_rect.left() < 0:
            new_rect.moveLeft(0)
        if new_rect.right() >= self.width():
            new_rect.moveRight(self.width() - 1)
        if new_rect.top() < 0:
            new_rect.moveTop(0)
        if new_rect.bottom() >= self.height():
            new_rect.moveBottom(self.height() - 1)

        self._selection_rect = new_rect

        # Update start/end points to match new selection
        if not self._is_selecting:
            self._start_point = self._selection_rect.topLeft()
            self._end_point = self._selection_rect.bottomRight()

        # Update size label
        w = self._selection_rect.width()
        h = self._selection_rect.height()
        self.size_label.setText(f"{w} x {h}")
        self.size_label.adjustSize()

        # Update label position
        label_x = self._selection_rect.right() - self.size_label.width()
        label_y = self._selection_rect.bottom() + 5
        if label_y + self.size_label.height() > self.height():
            label_y = self._selection_rect.top() - self.size_label.height() - 5
        if label_x < 0:
            label_x = self._selection_rect.left()
        self.size_label.move(label_x, label_y)

        self.update()

    def hideEvent(self, event):
        """Handle hide event - cleanup."""
        # Release keyboard grab before hiding
        self.releaseKeyboard()
        self._reset_state()
        self.size_label.hide()
        self.coord_label.hide()
        super().hideEvent(event)


class MultiScreenOverlay(QWidget):
    """
    Overlay that supports multiple monitors.
    Creates a virtual canvas spanning all screens.
    """

    captured = Signal(QPixmap)
    cancelled = Signal()

    # Constants for magnifier
    MAGNIFIER_SIZE = 120
    MAGNIFIER_ZOOM = 2.0
    MAGNIFIER_OFFSET = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._reset_state()

    def _setup_ui(self):
        """Setup the overlay UI."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Size label
        self.size_label = QLabel(self)
        self.size_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 120, 215, 200);
                color: white;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.size_label.hide()

        # Coordinate label for showing cursor position
        self.coord_label = QLabel(self)
        self.coord_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 11px;
                font-family: Consolas, monospace;
            }
        """)
        self.coord_label.hide()

        # Hint label
        self.hint_label = QLabel("拖拽选择区域，按 Esc 取消 | 方向键微调选区", self)
        self.hint_label.setStyleSheet("""
            QLabel {
                background-color: rgba(50, 50, 50, 180);
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
        """)

    def _reset_state(self):
        """Reset selection state."""
        self._is_selecting = False
        self._start_point = QPoint()
        self._end_point = QPoint()
        self._selection_rect = QRect()
        self._screen_pixmaps = []
        self._virtual_geometry = QRect()
        self._combined_pixmap = None
        self._current_cursor_pos = QPoint()

    def start(self):
        """Start the screenshot capture process."""
        self._reset_state()
        self._capture_all_screens()

        # Set geometry to cover all screens
        self.setGeometry(self._virtual_geometry)
        self.showFullScreen()

        # Show and position hint
        self.hint_label.adjustSize()
        x = (self.width() - self.hint_label.width()) // 2
        self.hint_label.move(x, 50)
        self.hint_label.show()

        # Grab keyboard focus (critical for receiving key events)
        self.activateWindow()
        self.setFocus()
        self.grabKeyboard()

    def _capture_all_screens(self):
        """Capture all screens and create combined pixmap."""
        screens = QGuiApplication.screens()
        if not screens:
            return

        # Calculate virtual geometry (bounding box of all screens)
        self._virtual_geometry = QRect()
        for screen in screens:
            self._virtual_geometry = self._virtual_geometry.united(screen.geometry())

        # Create combined pixmap
        self._combined_pixmap = QPixmap(
            self._virtual_geometry.width(),
            self._virtual_geometry.height()
        )
        self._combined_pixmap.fill(Qt.GlobalColor.black)

        painter = QPainter(self._combined_pixmap)

        # Capture each screen and draw to combined pixmap
        for screen in screens:
            geometry = screen.geometry()
            pixmap = screen.grabWindow(
                0,
                geometry.x(),
                geometry.y(),
                geometry.width(),
                geometry.height()
            )
            # Adjust position relative to virtual geometry
            x = geometry.x() - self._virtual_geometry.x()
            y = geometry.y() - self._virtual_geometry.y()
            painter.drawPixmap(x, y, pixmap)

        painter.end()

    def paintEvent(self, event):
        """Paint the overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw combined screen capture
        if self._combined_pixmap:
            painter.drawPixmap(0, 0, self._combined_pixmap)

        # Draw overlay
        overlay_color = QColor(0, 0, 0, 120)

        if self._selection_rect.isValid() and not self._selection_rect.isEmpty():
            rect = self._selection_rect.normalized()

            # Draw overlay regions
            painter.fillRect(0, 0, self.width(), rect.top(), overlay_color)
            painter.fillRect(0, rect.bottom() + 1, self.width(), self.height() - rect.bottom() - 1, overlay_color)
            painter.fillRect(0, rect.top(), rect.left(), rect.height(), overlay_color)
            painter.fillRect(rect.right() + 1, rect.top(), self.width() - rect.right() - 1, rect.height(), overlay_color)

            # Draw selection border
            pen = QPen(QColor(0, 120, 215), 2)
            painter.setPen(pen)
            painter.drawRect(rect)

            # Draw corner handles
            handle_size = 8
            painter.setBrush(QBrush(QColor(0, 120, 215)))
            painter.setPen(Qt.PenStyle.NoPen)
            for corner in [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]:
                painter.drawRect(corner.x() - handle_size // 2, corner.y() - handle_size // 2, handle_size, handle_size)
        else:
            painter.fillRect(self.rect(), overlay_color)

        # Draw magnifier at cursor position
        self._draw_magnifier(painter)

    def _draw_magnifier(self, painter):
        """Draw magnifier showing zoomed view at cursor position."""
        if not self._combined_pixmap or self._current_cursor_pos.isNull():
            return

        cursor_pos = self._current_cursor_pos
        mag_size = self.MAGNIFIER_SIZE
        zoom = self.MAGNIFIER_ZOOM
        offset = self.MAGNIFIER_OFFSET

        # Calculate magnifier position (avoid going off-screen)
        mag_x = cursor_pos.x() + offset
        mag_y = cursor_pos.y() + offset

        # Adjust if going off right edge
        if mag_x + mag_size > self.width():
            mag_x = cursor_pos.x() - mag_size - offset

        # Adjust if going off bottom edge
        if mag_y + mag_size > self.height():
            mag_y = cursor_pos.y() - mag_size - offset

        # Ensure within bounds
        mag_x = max(10, min(mag_x, self.width() - mag_size - 10))
        mag_y = max(10, min(mag_y, self.height() - mag_size - 10))

        # Calculate source rect (area around cursor to zoom)
        src_size = int(mag_size / zoom)
        src_x = cursor_pos.x() - src_size // 2
        src_y = cursor_pos.y() - src_size // 2

        # Clamp source rect to pixmap bounds
        src_x = max(0, min(src_x, self._combined_pixmap.width() - src_size))
        src_y = max(0, min(src_y, self._combined_pixmap.height() - src_size))

        # Create magnifier pixmap
        mag_pixmap = QPixmap(mag_size, mag_size)
        mag_pixmap.fill(Qt.GlobalColor.black)

        mag_painter = QPainter(mag_pixmap)
        mag_painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Draw zoomed portion
        source_rect = QRect(src_x, src_y, src_size, src_size)
        target_rect = QRect(0, 0, mag_size, mag_size)
        mag_painter.drawPixmap(target_rect, self._combined_pixmap, source_rect)

        # Draw crosshair in magnifier
        mag_painter.setPen(QPen(QColor(255, 0, 0), 1))
        center = mag_size // 2
        mag_painter.drawLine(center, 0, center, mag_size)
        mag_painter.drawLine(0, center, mag_size, center)

        mag_painter.end()

        # Draw magnifier background and border
        painter.setBrush(QBrush(QColor(40, 40, 40)))
        painter.setPen(QPen(QColor(0, 120, 215), 2))
        painter.drawRoundedRect(mag_x - 2, mag_y - 2, mag_size + 4, mag_size + 4, 6, 6)

        # Draw the magnifier pixmap
        painter.drawPixmap(mag_x, mag_y, mag_pixmap)

        # Draw cursor position info
        info_text = f"({cursor_pos.x()}, {cursor_pos.y()})"
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Consolas", 9))
        text_rect = painter.boundingRect(mag_x, mag_y + mag_size + 5, mag_size, 20, Qt.AlignmentFlag.AlignCenter, info_text)
        painter.fillRect(text_rect.adjusted(-4, -2, 4, 2), QColor(0, 0, 0, 180))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, info_text)

    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_selecting = True
            self._start_point = event.pos()
            self._end_point = event.pos()
            self._selection_rect = QRect(self._start_point, self._end_point)
            self.hint_label.hide()
            self.update()

    def mouseMoveEvent(self, event):
        """Handle mouse move."""
        # Update current cursor position for magnifier
        self._current_cursor_pos = event.pos()

        # Update coordinate label
        self.coord_label.setText(f"{self._current_cursor_pos.x()}, {self._current_cursor_pos.y()}")
        self.coord_label.adjustSize()

        # Position coordinate label near cursor but not overlapping
        coord_x = self._current_cursor_pos.x() + 15
        coord_y = self._current_cursor_pos.y() - self.coord_label.height() - 10

        # Keep on screen
        if coord_x + self.coord_label.width() > self.width():
            coord_x = self._current_cursor_pos.x() - self.coord_label.width() - 15
        if coord_y < 0:
            coord_y = self._current_cursor_pos.y() + 20

        self.coord_label.move(coord_x, coord_y)
        self.coord_label.show()

        if self._is_selecting:
            self._end_point = event.pos()
            self._selection_rect = QRect(self._start_point, self._end_point).normalized()

            w = self._selection_rect.width()
            h = self._selection_rect.height()
            self.size_label.setText(f"{w} x {h}")
            self.size_label.adjustSize()

            label_x = self._selection_rect.right() - self.size_label.width()
            label_y = self._selection_rect.bottom() + 5
            if label_y + self.size_label.height() > self.height():
                label_y = self._selection_rect.top() - self.size_label.height() - 5
            if label_x < 0:
                label_x = self._selection_rect.left()

            self.size_label.move(label_x, label_y)
            self.size_label.show()

        self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            self._selection_rect = QRect(self._start_point, event.pos()).normalized()

            if self._selection_rect.width() > 10 and self._selection_rect.height() > 10:
                self._capture_selection()
            else:
                self._selection_rect = QRect()
                self.size_label.hide()
                self.hint_label.show()
                self.update()

    def _capture_selection(self):
        """Capture the selected region."""
        if self._combined_pixmap and self._selection_rect.isValid():
            captured = self._combined_pixmap.copy(self._selection_rect)
            self.hide()
            self.captured.emit(captured)

    def keyPressEvent(self, event):
        """Handle key press - Esc to cancel, arrow keys to fine-tune selection."""
        if event.key() == Qt.Key.Key_Escape:
            # Reset selection state to prevent mouseReleaseEvent from capturing
            self._is_selecting = False
            self._selection_rect = QRect()
            # Hide all labels
            self.size_label.hide()
            self.coord_label.hide()
            self.hide()
            self.cancelled.emit()
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            # Fine-tune selection with arrow keys
            self._fine_tune_selection(event.key())
        else:
            super().keyPressEvent(event)

    def _fine_tune_selection(self, key):
        """Fine-tune selection rectangle by 1 pixel using arrow keys."""
        if not self._selection_rect.isValid() or self._selection_rect.isEmpty():
            return

        # Determine adjustment amount
        dx = 0
        dy = 0
        shift_modifier = QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
        step = 10 if shift_modifier else 1  # Shift + arrow = 10 pixels

        if key == Qt.Key.Key_Left:
            dx = -step
        elif key == Qt.Key.Key_Right:
            dx = step
        elif key == Qt.Key.Key_Up:
            dy = -step
        elif key == Qt.Key.Key_Down:
            dy = step

        # Adjust selection rectangle
        rect = self._selection_rect.normalized()
        new_rect = QRect(rect)

        # If currently selecting (dragging), adjust end point
        # Otherwise adjust the entire selection
        if self._is_selecting:
            new_rect = QRect(rect.topLeft(), rect.bottomRight() + QPoint(dx, dy))
        else:
            # Move entire selection
            new_rect = rect.translated(dx, dy)

        # Ensure selection stays within screen bounds
        if new_rect.left() < 0:
            new_rect.moveLeft(0)
        if new_rect.right() >= self.width():
            new_rect.moveRight(self.width() - 1)
        if new_rect.top() < 0:
            new_rect.moveTop(0)
        if new_rect.bottom() >= self.height():
            new_rect.moveBottom(self.height() - 1)

        self._selection_rect = new_rect

        # Update start/end points to match new selection
        if not self._is_selecting:
            self._start_point = self._selection_rect.topLeft()
            self._end_point = self._selection_rect.bottomRight()

        # Update size label
        w = self._selection_rect.width()
        h = self._selection_rect.height()
        self.size_label.setText(f"{w} x {h}")
        self.size_label.adjustSize()

        # Update label position
        label_x = self._selection_rect.right() - self.size_label.width()
        label_y = self._selection_rect.bottom() + 5
        if label_y + self.size_label.height() > self.height():
            label_y = self._selection_rect.top() - self.size_label.height() - 5
        if label_x < 0:
            label_x = self._selection_rect.left()
        self.size_label.move(label_x, label_y)

        self.update()

    def hideEvent(self, event):
        """Handle hide event."""
        # Release keyboard grab before hiding
        self.releaseKeyboard()
        self._reset_state()
        self.size_label.hide()
        self.coord_label.hide()
        super().hideEvent(event)
