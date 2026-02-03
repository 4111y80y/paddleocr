#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ScreenOCR - OCR Engine Wrapper
Encapsulates PaddleOCR functionality with device selection support.
Supports PaddleOCR 3.0 + PP-OCRv5
"""

import os
import sys
from typing import List, Tuple, Optional, Any

# 注意: os.environ 对 PaddlePaddle 3.x 无效
# 必须在 import paddle 之后使用 paddle.set_flags() 设置
# 见 _ensure_initialized() 方法中的 _setup_paddle_flags() 调用


def _setup_paddle_flags():
    """Setup PaddlePaddle flags to disable oneDNN and PIR.

    CRITICAL: Must be called AFTER 'import paddle' but BEFORE using any paddle features.
    os.environ is ineffective for PaddlePaddle 3.x, must use paddle.set_flags().
    Reference: https://github.com/PaddlePaddle/Paddle/issues/77340
    """
    try:
        import paddle
        # Disable PIR and oneDNN to avoid ConvertPirAttribute2RuntimeAttribute error
        paddle.set_flags({
            'FLAGS_enable_pir_api': 0,
            'FLAGS_use_mkldnn': 0,
        })
    except Exception:
        pass  # Ignore errors, will be handled elsewhere


class OCREngine:
    """
    OCR Engine wrapper for PaddleOCR.
    Supports CPU and multi-GPU device selection.
    Compatible with PaddleOCR 3.0 + PP-OCRv5
    """

    def __init__(self, device_id: str = "cpu", lang: str = "ch", model_type: str = "pp-ocrv5"):
        """
        Initialize OCR engine.

        Args:
            device_id: Device identifier ("cpu", "gpu:0", "gpu:1", etc.)
            lang: OCR language ("ch", "en", "cht", "japan", "korean", etc.)
            model_type: OCR model type ("pp-ocrv5", "paddleocr-vl")
        """
        self._device_id = device_id
        self._lang = lang
        self._model_type = model_type
        self._ocr = None
        self._paddle = None
        self._initialized = False
        self._ocr_version = None
        self._vl_pipeline = None  # For PaddleOCR-VL-1.5
        self._structure_engine = None  # For PP-StructureV3 (cached)

        # Lazy initialization - don't load heavy modules until needed

    def _ensure_initialized(self):
        """Ensure PaddleOCR is initialized."""
        if self._initialized:
            return

        try:
            import paddle
            # Setup flags immediately after import, before any paddle operations
            _setup_paddle_flags()
            self._paddle = paddle

            # Set device
            paddle.set_device(self._device_id)

            # Check if using VL model
            if self._model_type == 'paddleocr-vl':
                self._init_vl_model()
            else:
                self._init_ppocr_model()

            self._initialized = True

        except ImportError as e:
            raise RuntimeError(
                f"Failed to import PaddleOCR. "
                f"Please install: pip install paddlepaddle-gpu paddleocr\n"
                f"Error: {e}"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize OCR engine: {e}")

    def _init_ppocr_model(self):
        """Initialize PP-OCRv5 model."""
        from paddleocr import PaddleOCR

        # Detect PaddleOCR version
        import paddleocr as paddleocr_module
        self._ocr_version = getattr(paddleocr_module, '__version__', '2.x')

        use_gpu = self._device_id.startswith("gpu")
        gpu_id = 0
        if use_gpu and ":" in self._device_id:
            gpu_id = int(self._device_id.split(":")[1])

        # Check if PaddleOCR 3.0+ (PP-OCRv5)
        if self._is_version_3_or_higher():
            # PaddleOCR 3.0+ API - uses PP-OCRv5 model by default
            # Note: use_gpu and show_log parameters removed in 3.0+
            # device is set via paddle.set_device()
            self._ocr = PaddleOCR(lang=self._lang)
        else:
            # PaddleOCR 2.x API (backward compatibility)
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self._lang,
                use_gpu=use_gpu,
                gpu_id=gpu_id,
                show_log=False
            )

    def _init_vl_model(self):
        """Initialize PaddleOCR-VL-1.5 vision-language model."""
        try:
            from paddleocr import PaddleOCRVL
        except ImportError:
            raise RuntimeError(
                "PaddleOCR-VL-1.5 not available. "
                "Please install PaddleOCR 3.0+: pip install 'paddleocr>=3.0'"
            )

        use_gpu = self._device_id.startswith("gpu")

        # Initialize VL model with 0.9B parameters
        self._vl_pipeline = PaddleOCRVL(
            use_gpu=use_gpu,
            device=self._device_id if use_gpu else "cpu",
            lang=self._lang,
            show_log=False
        )
        self._ocr_version = "3.0-vl"

    def _is_version_3_or_higher(self) -> bool:
        """Check if PaddleOCR version is 3.0 or higher."""
        if self._ocr_version is None:
            return False
        try:
            version_parts = str(self._ocr_version).split('.')
            major_version = int(version_parts[0])
            return major_version >= 3
        except (ValueError, IndexError):
            return False

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
            self._vl_pipeline = None

    def set_model_type(self, model_type: str):
        """
        Set the OCR model type.

        Args:
            model_type: Model type ("pp-ocrv5", "paddleocr-vl")
        """
        if model_type != self._model_type:
            self._model_type = model_type
            # Force re-initialization on next use
            self._initialized = False
            self._ocr = None
            self._vl_pipeline = None

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

        # Use VL model if selected
        if self._model_type == 'paddleocr-vl' and self._vl_pipeline is not None:
            return self._recognize_vl(img)

        # Run OCR using the appropriate API
        if self._is_version_3_or_higher():
            # PaddleOCR 3.0+ uses predict() method
            try:
                result = self._ocr.predict(img)
            except Exception:
                # Fallback to ocr() if predict fails
                result = self._ocr.ocr(img, cls=True)
        else:
            # PaddleOCR 2.x uses ocr() method
            result = self._ocr.ocr(img, cls=True)

        # Extract text from result
        return self._extract_text(result)

    def _recognize_vl(self, image_input: Any) -> str:
        """
        Perform OCR using PaddleOCR-VL-1.5 vision-language model.

        Args:
            image_input: Image path (str), PIL Image, or numpy array.

        Returns:
            Recognized text as a single string.
        """
        # Convert input to path if needed
        temp_path = None
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Image not found: {image_input}")
            img_path = image_input
        elif hasattr(image_input, 'convert'):
            # PIL Image - save to temp file
            import tempfile
            temp_path = tempfile.mktemp(suffix='.png')
            image_input.save(temp_path, 'PNG')
            img_path = temp_path
        else:
            # Assume numpy array - save to temp file
            import tempfile
            from PIL import Image
            temp_path = tempfile.mktemp(suffix='.png')
            Image.fromarray(image_input).save(temp_path, 'PNG')
            img_path = temp_path

        try:
            # Run VL model prediction
            result = self._vl_pipeline.predict(img_path)

            # Extract text from VL result
            texts = []
            for res in result:
                if hasattr(res, 'text') and res.text:
                    texts.append(str(res.text))
                elif isinstance(res, dict):
                    text = res.get('text', '')
                    if text:
                        texts.append(str(text))

            return '\n'.join(texts)

        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def recognize_with_confidence(self, image_input: Any) -> List[Tuple[str, float]]:
        """
        Perform OCR on an image and return text with confidence scores.

        Args:
            image_input: Image path (str), PIL Image, or numpy array.

        Returns:
            List of (text, confidence) tuples.
        """
        self._ensure_initialized()

        # Use VL model if selected (VL model returns text without confidence)
        if self._model_type == 'paddleocr-vl' and self._vl_pipeline is not None:
            text = self._recognize_vl(image_input)
            # VL model doesn't provide confidence, return 1.0 for each line
            return [(line, 1.0) for line in text.split('\n') if line.strip()]

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

        # Run OCR using the appropriate API
        if self._is_version_3_or_higher():
            # PaddleOCR 3.0+ uses predict() method
            try:
                result = self._ocr.predict(img)
            except Exception:
                # Fallback to ocr() if predict fails
                result = self._ocr.ocr(img, cls=True)
        else:
            # PaddleOCR 2.x uses ocr() method
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

        # Run OCR using the appropriate API
        if self._is_version_3_or_higher():
            # PaddleOCR 3.0+ uses predict() method
            try:
                result = self._ocr.predict(img)
            except Exception:
                # Fallback to ocr() if predict fails
                result = self._ocr.ocr(img, cls=True)
        else:
            # PaddleOCR 2.x uses ocr() method
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
        if self._vl_pipeline is not None:
            try:
                if hasattr(self._vl_pipeline, 'close'):
                    self._vl_pipeline.close()
            except Exception:
                pass
            self._vl_pipeline = None
        if self._structure_engine is not None:
            self._structure_engine = None
        self._ocr = None
        self._initialized = False

    def recognize_document(self, image_input: Any) -> dict:
        """
        Perform document structure analysis using PP-StructureV3.
        Returns markdown and JSON format output.

        Args:
            image_input: Image path (str), PIL Image, or numpy array.

        Returns:
            Dictionary with 'markdown', 'json', and 'text' keys.
        """
        try:
            from paddleocr import PPStructureV3
        except ImportError:
            raise RuntimeError(
                "PP-StructureV3 not available. "
                "Please install PaddleOCR: pip install 'paddleocr>=3.0' paddlex"
            )

        # Convert input to path or array
        temp_path = None
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Image not found: {image_input}")
            img_path = image_input
        elif hasattr(image_input, 'convert'):
            # PIL Image - convert to numpy array
            import numpy as np
            img_array = np.array(image_input.convert('RGB'))
            img_path = None
        else:
            # Assume numpy array
            img_array = image_input
            img_path = None

        try:
            # Use cached PP-StructureV3 engine or create new one
            # Use format_block_content=True to get automatic Markdown formatting
            if self._structure_engine is None:
                self._structure_engine = PPStructureV3(
                    lang=self._lang,
                    format_block_content=True  # Enable Markdown output
                )

            # Run prediction - pass image path directly if available
            if img_path is not None:
                output = self._structure_engine.predict(img_path, format_block_content=True)
            else:
                # For numpy array, need to use cv2 format (BGR)
                import cv2
                img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                output = self._structure_engine.predict(img, format_block_content=True)

            # Extract results
            result = {
                'markdown': '',
                'json': [],
                'text': ''
            }

            # Parse PP-StructureV3 output format
            # output is a list of page results, each page_result is a special object
            all_texts = []
            markdown_pages = []
            raw_results = []

            for page_result in output:
                # Store raw result for JSON output
                # Filter out internal objects (fields starting with _) and non-serializable objects
                if hasattr(page_result, '__dict__'):
                    page_dict = {}
                    for k, v in page_result.__dict__.items():
                        # Skip internal fields (starting with _) and numpy arrays
                        if k.startswith('_'):
                            continue
                        if hasattr(v, 'ndim'):  # Skip numpy arrays
                            continue
                        # Skip non-serializable objects (writers, etc.)
                        if hasattr(v, '__dict__') and not isinstance(v, (dict, list, str, int, float, bool, type(None))):
                            continue
                        page_dict[k] = v
                    raw_results.append(page_dict)
                elif isinstance(page_result, dict):
                    raw_results.append(page_result)

                # Try to get markdown text from page_result
                # PP-StructureV3 returns MarkdownResult with markdown_texts field
                page_markdown = ''

                # First try markdown_texts (direct field on page_result)
                if hasattr(page_result, 'markdown_texts') and page_result.markdown_texts:
                    page_markdown = str(page_result.markdown_texts)
                # Then try markdown.markdown_texts if markdown is an object
                elif hasattr(page_result, 'markdown'):
                    md_val = page_result.markdown
                    if md_val is not None:
                        # Check if it has markdown_texts attribute
                        if hasattr(md_val, 'markdown_texts') and md_val.markdown_texts:
                            page_markdown = str(md_val.markdown_texts)
                        elif isinstance(md_val, str):
                            page_markdown = md_val
                        elif isinstance(md_val, dict) and 'markdown_texts' in md_val:
                            page_markdown = str(md_val['markdown_texts'])
                # Dict access
                elif isinstance(page_result, dict):
                    if 'markdown_texts' in page_result:
                        page_markdown = str(page_result['markdown_texts'])
                    elif 'markdown' in page_result:
                        md_val = page_result['markdown']
                        if isinstance(md_val, dict) and 'markdown_texts' in md_val:
                            page_markdown = str(md_val['markdown_texts'])
                        elif isinstance(md_val, str):
                            page_markdown = md_val

                if page_markdown:
                    markdown_pages.append(page_markdown)

                # Extract text from boxes if available
                boxes = None
                if hasattr(page_result, 'boxes'):
                    boxes = page_result.boxes
                elif isinstance(page_result, dict) and 'boxes' in page_result:
                    boxes = page_result.get('boxes', [])

                if boxes:
                    for box in boxes:
                        if isinstance(box, dict):
                            # Try various text field names
                            for text_key in ['text', 'rec_text', 'content', 'ocr_text']:
                                if text_key in box:
                                    text_val = box[text_key]
                                    if isinstance(text_val, str) and text_val.strip():
                                        all_texts.append(text_val.strip())
                                        break
                                    elif isinstance(text_val, list):
                                        for t in text_val:
                                            if isinstance(t, str) and t.strip():
                                                all_texts.append(t.strip())
                                            elif isinstance(t, dict) and 'text' in t:
                                                all_texts.append(str(t['text']).strip())
                                        break

                # Also try to get text from ocr_res if boxes didn't have text
                if not all_texts:
                    ocr_res = None
                    if hasattr(page_result, 'ocr_res'):
                        ocr_res = page_result.ocr_res
                    elif isinstance(page_result, dict) and 'ocr_res' in page_result:
                        ocr_res = page_result.get('ocr_res')

                    if ocr_res:
                        if hasattr(ocr_res, 'rec_texts'):
                            all_texts.extend(ocr_res.rec_texts or [])
                        elif isinstance(ocr_res, dict) and 'rec_texts' in ocr_res:
                            all_texts.extend(ocr_res.get('rec_texts', []))

            # Try to concatenate markdown pages if PPStructureV3 provides the method
            if markdown_pages:
                try:
                    md_result = self._structure_engine.concatenate_markdown_pages(markdown_pages)
                    # Ensure result is string
                    result['markdown'] = str(md_result) if not isinstance(md_result, str) else md_result
                except Exception:
                    result['markdown'] = '\n\n'.join(str(p) for p in markdown_pages)
            else:
                # Fallback: build markdown from extracted text
                result['markdown'] = '\n'.join(all_texts) if all_texts else ''

            result['json'] = raw_results
            # For text: use extracted texts, or fall back to markdown content
            if all_texts:
                result['text'] = '\n'.join(all_texts)
            elif markdown_pages:
                # Use markdown content as plain text fallback
                result['text'] = '\n'.join(markdown_pages)
            else:
                result['text'] = self._extract_text_from_structure(raw_results)

            return result

        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def _extract_text_from_structure(self, json_data: Any) -> str:
        """Extract plain text from structure JSON data."""
        texts = []

        # Safe check for empty/None data (avoid NumPy array truth value error)
        if json_data is None:
            return ''

        # Check for numpy array
        if hasattr(json_data, 'ndim'):
            # This is a numpy array, skip it
            return ''

        # Handle different JSON structures
        if isinstance(json_data, list):
            for item in json_data:
                texts.append(self._extract_text_from_structure(item))
        elif isinstance(json_data, dict):
            # Try common text fields
            for key in ['text', 'content', 'ocr_text', 'rec_texts']:
                if key in json_data:
                    value = json_data[key]
                    if isinstance(value, list):
                        texts.extend([str(t) for t in value])
                    elif isinstance(value, str):
                        texts.append(value)

            # Recursively process nested structures
            for key, value in json_data.items():
                if isinstance(value, (dict, list)) and key not in ['text', 'content', 'ocr_text', 'rec_texts']:
                    texts.append(self._extract_text_from_structure(value))

        return '\n'.join(filter(None, texts))

    def get_version_info(self) -> dict:
        """
        Get version information of PaddleOCR and PaddlePaddle.

        Returns:
            Dictionary with version information.
        """
        info = {
            'paddleocr_version': 'unknown',
            'paddlepaddle_version': 'unknown',
            'is_v3_or_higher': False
        }

        try:
            import paddleocr as paddleocr_module
            info['paddleocr_version'] = getattr(paddleocr_module, '__version__', 'unknown')
            # Check version directly from module
            version_parts = str(info['paddleocr_version']).split('.')
            info['is_v3_or_higher'] = int(version_parts[0]) >= 3
        except Exception:
            pass

        try:
            import paddle
            info['paddlepaddle_version'] = getattr(paddle, '__version__', 'unknown')
        except Exception:
            pass

        return info

    def get_model_type(self) -> str:
        """Get current OCR model type."""
        return self._model_type

    def get_model_display_name(self) -> str:
        """Get display name for current model."""
        model_names = {
            'pp-ocrv5': 'PP-OCRv5',
            'paddleocr-vl': 'PaddleOCR-VL-1.5'
        }
        return model_names.get(self._model_type, self._model_type)
