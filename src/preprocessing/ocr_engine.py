"""OCR engine wrapper with multi-engine fallback for image-based patents.

Priority: PaddleOCR (best Chinese+English) → EasyOCR (cross-platform fallback)
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class OCREngine:
    """Multi-engine OCR with automatic fallback.

    Tries PaddleOCR first (best accuracy for Chinese+English mixed text),
    falls back to EasyOCR (pure Python, cross-platform, no oneDNN dependency).
    """

    def __init__(self, use_gpu: bool = False):
        self._ocr = None
        self._engine_name = None
        self.use_gpu = use_gpu

    @property
    def ocr(self):
        if self._ocr is None:
            self._init_engine()
        return self._ocr

    @property
    def engine_name(self) -> str:
        if self._engine_name is None:
            self._init_engine()
        return self._engine_name or "none"

    def _init_engine(self):
        """Try PaddleOCR first, fall back to EasyOCR."""
        # Try PaddleOCR first
        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                use_textline_orientation=True,
                lang="ch",
                use_gpu=self.use_gpu,
            )
            # Quick sanity check
            self._engine_name = "paddleocr"
            logger.info("OCR engine: PaddleOCR")
            return
        except Exception as e:
            logger.info(f"PaddleOCR unavailable: {e}")

        # Fall back to EasyOCR
        try:
            import easyocr
            self._ocr = easyocr.Reader(
                ["ch_sim", "en"],
                gpu=self.use_gpu,
                verbose=False,
            )
            self._engine_name = "easyocr"
            logger.info("OCR engine: EasyOCR (fallback)")
        except ImportError:
            logger.error(
                "No OCR engine available. Install paddleocr or easyocr."
            )
            raise

    def recognize(self, image_path: str) -> str:
        """Run OCR and return recognized text."""
        if self.engine_name == "paddleocr":
            return self._recognize_paddle(image_path)
        elif self.engine_name == "easyocr":
            return self._recognize_easyocr(image_path)
        return ""

    def _recognize_paddle(self, image_path: str) -> str:
        try:
            result = self._ocr.predict(image_path)
            if not result:
                return ""
            lines = []
            if isinstance(result, list):
                for item in result:
                    if item is None:
                        continue
                    if isinstance(item, dict):
                        t = item.get("rec_text", "")
                        if t:
                            lines.append(t)
                    elif isinstance(item, (list, tuple)) and len(item) >= 2:
                        if isinstance(item[1], (list, tuple)):
                            lines.append(str(item[1][0]))
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"PaddleOCR error: {e}")
            # Fallback to easyocr if paddle fails at runtime
            try:
                return self._recognize_easyocr(image_path)
            except Exception:
                return ""

    def _recognize_easyocr(self, image_path: str) -> str:
        try:
            result = self._ocr.readtext(image_path)
            if not result:
                return ""
            # EasyOCR returns: [(bbox, text, confidence), ...]
            # Sort by reading order (top-to-bottom, left-to-right)
            result.sort(key=lambda r: (r[0][0][1], r[0][0][0]))
            return "\n".join(r[1] for r in result if r[2] > 0.3)
        except Exception as e:
            logger.error(f"EasyOCR error: {e}")
            return ""
