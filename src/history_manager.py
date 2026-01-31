#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ScreenOCR - History Manager
Manages OCR history records with persistence.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class HistoryRecord:
    """Single OCR history record."""
    id: str
    timestamp: str
    text: str
    image_thumbnail: Optional[str]  # Base64 encoded thumbnail
    elapsed_time: float

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'HistoryRecord':
        return HistoryRecord(**data)


class HistoryManager:
    """Manages OCR history with file persistence."""

    MAX_RECORDS = 100  # Maximum number of records to keep
    THUMBNAIL_SIZE = (120, 120)  # Thumbnail dimensions

    def __init__(self, storage_dir: Optional[str] = None):
        """Initialize history manager.

        Args:
            storage_dir: Directory to store history file.
                         Defaults to user's app data directory.
        """
        if storage_dir is None:
            # Use user's local app data directory
            if os.name == 'nt':
                base_dir = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
            else:
                base_dir = os.path.expanduser('~/.local/share')
            storage_dir = os.path.join(base_dir, 'ScreenOCR')

        self.storage_dir = storage_dir
        self.history_file = os.path.join(storage_dir, 'history.json')
        self._records: List[HistoryRecord] = []

        # Ensure storage directory exists
        os.makedirs(storage_dir, exist_ok=True)

        # Load existing history
        self._load()

    def _load(self):
        """Load history from file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._records = [HistoryRecord.from_dict(r) for r in data]
            except Exception as e:
                print(f"[WARNING] Failed to load history: {e}")
                self._records = []

    def _save(self):
        """Save history to file."""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([r.to_dict() for r in self._records], f,
                         ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] Failed to save history: {e}")

    def add_record(self, text: str, image=None, elapsed_time: float = 0.0) -> HistoryRecord:
        """Add a new history record.

        Args:
            text: OCR result text
            image: PIL Image or QPixmap (optional, for thumbnail)
            elapsed_time: OCR processing time in seconds

        Returns:
            The created HistoryRecord
        """
        # Generate unique ID
        record_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Generate thumbnail if image provided
        thumbnail_b64 = None
        if image is not None:
            thumbnail_b64 = self._create_thumbnail(image)

        record = HistoryRecord(
            id=record_id,
            timestamp=timestamp,
            text=text,
            image_thumbnail=thumbnail_b64,
            elapsed_time=elapsed_time
        )

        # Add to beginning of list (newest first)
        self._records.insert(0, record)

        # Trim to max records
        if len(self._records) > self.MAX_RECORDS:
            self._records = self._records[:self.MAX_RECORDS]

        # Save to file
        self._save()

        return record

    def _create_thumbnail(self, image) -> Optional[str]:
        """Create base64 encoded thumbnail from image.

        Args:
            image: PIL Image or QPixmap

        Returns:
            Base64 encoded JPEG string or None
        """
        try:
            import base64
            from io import BytesIO

            # Convert QPixmap to PIL Image if needed
            if hasattr(image, 'toImage'):
                # QPixmap
                from PySide6.QtCore import QBuffer, QIODevice
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                image.save(buffer, "PNG")

                from PIL import Image
                img_data = bytes(buffer.data())
                pil_image = Image.open(BytesIO(img_data))
            elif hasattr(image, 'thumbnail'):
                # Already PIL Image
                pil_image = image.copy()
            else:
                return None

            # Create thumbnail
            pil_image.thumbnail(self.THUMBNAIL_SIZE)

            # Convert to base64
            buffer = BytesIO()
            pil_image.save(buffer, format='JPEG', quality=70)
            thumbnail_b64 = base64.b64encode(buffer.getvalue()).decode('ascii')

            return thumbnail_b64

        except Exception as e:
            print(f"[WARNING] Failed to create thumbnail: {e}")
            return None

    def get_records(self, limit: int = 50, offset: int = 0) -> List[HistoryRecord]:
        """Get history records.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of HistoryRecord
        """
        return self._records[offset:offset + limit]

    def get_record_by_id(self, record_id: str) -> Optional[HistoryRecord]:
        """Get a specific record by ID.

        Args:
            record_id: Record ID

        Returns:
            HistoryRecord or None if not found
        """
        for record in self._records:
            if record.id == record_id:
                return record
        return None

    def delete_record(self, record_id: str) -> bool:
        """Delete a record by ID.

        Args:
            record_id: Record ID to delete

        Returns:
            True if deleted, False if not found
        """
        for i, record in enumerate(self._records):
            if record.id == record_id:
                del self._records[i]
                self._save()
                return True
        return False

    def clear_all(self):
        """Clear all history records."""
        self._records = []
        self._save()

    def get_count(self) -> int:
        """Get total number of records."""
        return len(self._records)

    def search(self, query: str, limit: int = 50) -> List[HistoryRecord]:
        """Search history by text content.

        Args:
            query: Search query string
            limit: Maximum results to return

        Returns:
            List of matching HistoryRecord
        """
        query_lower = query.lower()
        results = []
        for record in self._records:
            if query_lower in record.text.lower():
                results.append(record)
                if len(results) >= limit:
                    break
        return results
