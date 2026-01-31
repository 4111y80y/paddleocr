#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ScreenOCR - OCR Engine Wrapper
Encapsulates PaddleOCR functionality with device selection support.
"""

import os
import sys
from typing import List, Tuple, Optional, Any


class OCREngine:
    """
    OCR Engine wrapper for PaddleOCR.
    Supports CPU and multi-GPU device selection.
    """

    def __init__(self, device_id: str = "cpu", lang: str = "ch"):
        """
        Initialize OCR engine.

        Args:
            device_id: Device identifier ("cpu", "gpu:0", "gpu:1", etc.)
            lang: OCR language ("ch", "en", "cht", "japan", "korean", etc.)
        """
        self._device_id = device_id
        self._lang = lang
        self._ocr = None
        self._paddle = None
        self._initialized = False

        # Lazy initialization - don't load heavy modules until needed

    def _ensure_initialized(self):
        """Ensure PaddleOCR is initialized."""
        if self._initialized:
            return

        try:
            import paddle
            self._paddle = paddle

            # Set device
            paddle.set_device(self._device_id)

            # Import and initialize PaddleOCR
            from paddleocr import PaddleOCR

            use_gpu = self._device_id.startswith("gpu")
            gpu_id = 0
            if use_gpu and ":" in self._device_id:
                gpu_id = int(self._device_id.split(":")[1])

            # PaddleOCR 2.7.x API
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self._lang,
                use_gpu=use_gpu,
                gpu_id=gpu_id,
                show_log=False
            )

            self._initialized = True

        except ImportError as e:
            raise RuntimeError(
                f"Failed to import PaddleOCR. "
                f"Please install: pip install paddlepaddle paddleocr\n"
                f"Error: {e}"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize OCR engine: {e}")

    def get_available_devices(self) -> List[Tuple[str, str]]:
        """
        Get list of available computing devices.

        Returns:
            List of (display_name, device_id) tuples.
        """
        devices = [("CPU", "cpu")]

        try:
            import paddle

            if paddle.device.is_compiled_with_cuda():
                gpu_count = paddle.device.cuda.device_count()
                for i in range(gpu_count):
                    try:
                        name = paddle.device.cuda.get_device_name(i)
                        devices.append((f"GPU {i}: {name}", f"gpu:{i}"))
                    except Exception:
                        devices.append((f"GPU {i}", f"gpu:{i}"))
        except ImportError:
            pass
        except Exception as e:
            print(f"[WARNING] Failed to detect GPU devices: {e}")

        return devices

    def set_device(self, device_id: str):
        """
        Set the computing device.

        Args:
            device_id: Device identifier ("cpu", "gpu:0", etc.)
        """
        if device_id != self._device_id:
            self._device_id = device_id
            # Force re-initialization on next use
            self._initialized = False
            self._ocr = None

    def set_language(self, lang: str):
        """
        Set the OCR language.

        Args:
            lang: OCR language ("ch", "en", etc.)
        """
        if lang != self._lang:
            self._lang = lang
            # Force re-initialization on next use
            self._initialized = False
            self._ocr = None

    def get_current_device_name(self) -> str:
        """Get the display name of current device."""
        if self._device_id == "cpu":
            return "CPU"

        if self._device_id.startswith("gpu"):
            try:
                import paddle
                if ":" in self._device_id:
                    gpu_id = int(self._device_id.split(":")[1])
                else:
                    gpu_id = 0
                name = paddle.device.cuda.get_device_name(gpu_id)
                return f"GPU {gpu_id}: {name}"
            except Exception:
                return self._device_id.upper()

        return self._device_id

    def recognize(self, image_input: Any) -> str:
        """
        Perform OCR on an image.

        Args:
            image_input: Image path (str), PIL Image, or numpy array.

        Returns:
            Recognized text as a single string.
        """
        self._ensure_initialized()

        # Convert input to path or array
        if isinstance(image_input, str):
            # File path
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Image not found: {image_input}")
            img = image_input
        elif hasattr(image_input, 'convert'):
            # PIL Image - convert to numpy array
            import numpy as np
            img = np.array(image_input.convert('RGB'))
        else:
            # Assume numpy array
            img = image_input

        # Run OCR using the new predict API
        try:
            result = self._ocr.predict(img)
        except AttributeError:
            # Fallback to old API
            result = self._ocr.ocr(img, cls=True)

        # Extract text from result
        return self._extract_text(result)

    def recognize_with_confidence(self, image_input: Any) -> List[Tuple[str, float]]:
        """
        Perform OCR on an image and return text with confidence scores.

        Args:
            image_input: Image path (str), PIL Image, or numpy array.

        Returns:
            List of (text, confidence) tuples.
        """
        self._ensure_initialized()

        # Convert input
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Image not found: {image_input}")
            img = image_input
        elif hasattr(image_input, 'convert'):
            import numpy as np
            img = np.array(image_input.convert('RGB'))
        else:
            img = image_input

        # Run OCR
        try:
            result = self._ocr.predict(img)
        except AttributeError:
            result = self._ocr.ocr(img, cls=True)

        return self._extract_with_confidence(result)

    def _extract_with_confidence(self, result: Any) -> List[Tuple[str, float]]:
        """
        Extract text with confidence scores from OCR result.

        Args:
            result: Raw OCR result from PaddleOCR.

        Returns:
            List of (text, confidence) tuples.
        """
        items = []

        if not result:
            return items

        if isinstance(result, list):
            for page_result in result:
                if isinstance(page_result, dict):
                    # New predict API format
                    texts = page_result.get('rec_texts', [])
                    scores = page_result.get('rec_scores', [])

                    for i, text in enumerate(texts):
                        score = scores[i] if i < len(scores) else 1.0
                        items.append((text, float(score)))

                elif isinstance(page_result, list):
                    # Old ocr API format
                    for item in page_result:
                        if item and len(item) >= 2:
                            text_info = item[1]
                            if isinstance(text_info, tuple) and len(text_info) >= 2:
                                text, score = text_info[0], float(text_info[1])
                            else:
                                text, score = str(text_info), 1.0
                            items.append((text, score))

        return items

    def _extract_text(self, result: Any) -> str:
        """
        Extract text from PaddleOCR result.

        Args:
            result: Raw OCR result from PaddleOCR.

        Returns:
            Extracted text as a single string.
        """
        if not result:
            return ""

        lines = []

        # Handle different result formats
        # New API format: list of dicts with 'rec_texts' key
        if isinstance(result, list):
            for page_result in result:
                if isinstance(page_result, dict):
                    # New predict API format
                    if 'rec_texts' in page_result:
                        texts = page_result['rec_texts']
                        if isinstance(texts, list):
                            lines.extend(texts)
                        else:
                            lines.append(str(texts))
                elif isinstance(page_result, list):
                    # Old ocr API format: [[box, (text, confidence)], ...]
                    for item in page_result:
                        if item and len(item) >= 2:
                            text_info = item[1]
                            if isinstance(text_info, tuple) and len(text_info) >= 1:
                                lines.append(text_info[0])
                            elif isinstance(text_info, str):
                                lines.append(text_info)

        return '\n'.join(lines)

    def recognize_with_boxes(self, image_input: Any) -> List[Tuple[List, str, float]]:
        """
        Perform OCR and return results with bounding boxes.

        Args:
            image_input: Image path, PIL Image, or numpy array.

        Returns:
            List of (box, text, confidence) tuples.
        """
        self._ensure_initialized()

        # Convert input
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Image not found: {image_input}")
            img = image_input
        elif hasattr(image_input, 'convert'):
            import numpy as np
            img = np.array(image_input.convert('RGB'))
        else:
            img = image_input

        # Run OCR
        try:
            result = self._ocr.predict(img)
        except AttributeError:
            result = self._ocr.ocr(img, cls=True)

        return self._extract_with_boxes(result)

    def _extract_with_boxes(self, result: Any) -> List[Tuple[List, str, float]]:
        """Extract text with bounding boxes from OCR result."""
        items = []

        if not result:
            return items

        if isinstance(result, list):
            for page_result in result:
                if isinstance(page_result, dict):
                    # New predict API format
                    boxes = page_result.get('dt_polys', [])
                    texts = page_result.get('rec_texts', [])
                    scores = page_result.get('rec_scores', [])

                    for i, (box, text) in enumerate(zip(boxes, texts)):
                        score = scores[i] if i < len(scores) else 1.0
                        items.append((box, text, score))

                elif isinstance(page_result, list):
                    # Old ocr API format
                    for item in page_result:
                        if item and len(item) >= 2:
                            box = item[0]
                            text_info = item[1]
                            if isinstance(text_info, tuple) and len(text_info) >= 2:
                                text, score = text_info[0], text_info[1]
                            else:
                                text, score = str(text_info), 1.0
                            items.append((box, text, score))

        return items

    def cleanup(self):
        """Cleanup resources."""
        self._ocr = None
        self._initialized = False
