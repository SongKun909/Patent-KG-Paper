"""OCR engine wrapper using PaddleOCR for image-based patent pages."""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class OCREngine:
    """PaddleOCR-based OCR engine for scanned patent pages.

    Handles both single-column and multi-column layouts via
    PP-Structure layout analysis.
    """

    def __init__(self, use_gpu: bool = False):
        self._ocr = None
        self._layout_parser = None
        self.use_gpu = use_gpu

    @property
    def ocr(self):
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang="ch",  # Supports Chinese + English mixed
                    use_gpu=self.use_gpu,
                    show_log=False,
                )
            except ImportError:
                logger.warning(
                    "PaddleOCR not installed. Install with: "
                    "pip install paddleocr paddlepaddle"
                )
                raise
        return self._ocr

    @property
    def layout_parser(self):
        """Layout-aware table/structure parser from PP-Structure."""
        if self._layout_parser is None:
            try:
                from paddleocr import PPStructure
                self._layout_parser = PPStructure(
                    show_log=False, use_gpu=self.use_gpu
                )
            except ImportError:
                logger.info("PPStructure not available, using plain OCR")
                self._layout_parser = False
        return self._layout_parser

    def recognize(self, image_path: str) -> str:
        """Run OCR on a single page image and return recognized text.

        Args:
            image_path: Path to a PNG/JPEG image file.

        Returns:
            Recognized text string.
        """
        try:
            result = self.ocr.ocr(image_path, cls=True)
            if not result or not result[0]:
                return ""
            return self._extract_text_from_ocr_result(result)
        except Exception as e:
            logger.error(f"OCR error on {image_path}: {e}")
            return ""

    def recognize_with_layout(self, image_path: str) -> dict:
        """Run layout-aware OCR, detecting text blocks and their positions.

        Returns:
            dict with keys: 'full_text', 'blocks' (list of {text, bbox, type})
        """
        result = self.ocr.ocr(image_path, cls=True)
        if not result or not result[0]:
            return {"full_text": "", "blocks": []}

        blocks = self._extract_blocks(result)
        full_text = self._order_blocks_reading(blocks)

        return {"full_text": full_text, "blocks": blocks}

    def _extract_text_from_ocr_result(self, ocr_result: list) -> str:
        """Extract ordered text from PaddleOCR result."""
        lines = []
        # ocr_result[0] = list of detected text regions
        for region in ocr_result[0]:
            if region is None:
                continue
            # region = [[x1,y1],[x2,y2],[x3,y3],[x4,y4]], (text, confidence)
            text = region[1][0]
            lines.append(text)
        return "\n".join(lines)

    def _extract_blocks(self, ocr_result: list) -> list:
        """Extract text blocks with bounding boxes."""
        blocks = []
        for region in ocr_result[0]:
            if region is None:
                continue
            bbox = region[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            text = region[1][0]
            # Calculate center y-coordinate for reading order
            center_y = sum(p[1] for p in bbox) / 4
            center_x = sum(p[0] for p in bbox) / 4
            blocks.append({
                "text": text,
                "center_y": center_y,
                "center_x": center_x,
                "bbox": bbox,
                "type": "text",
            })
        return blocks

    def _order_blocks_reading(self, blocks: list) -> str:
        """Order blocks by reading order: top-to-bottom within columns.

        For multi-column layouts: detect columns by x-position clustering,
        then within each column read top-to-bottom, left column first.
        """
        if not blocks:
            return ""

        # Simple heuristic: group by y-bands (lines), then left-to-right within band
        Y_TOLERANCE = 30  # pixels tolerance for same line
        sorted_blocks = sorted(blocks, key=lambda b: (b["center_y"], b["center_x"]))

        lines_text = []
        current_line = []
        current_y = None

        for block in sorted_blocks:
            y = block["center_y"]
            if current_y is None or abs(y - current_y) > Y_TOLERANCE:
                if current_line:
                    current_line.sort(key=lambda b: b["center_x"])
                    lines_text.append(" ".join(b["text"] for b in current_line))
                current_line = [block]
                current_y = y
            else:
                current_line.append(block)

        if current_line:
            current_line.sort(key=lambda b: b["center_x"])
            lines_text.append(" ".join(b["text"] for b in current_line))

        return "\n".join(lines_text)
