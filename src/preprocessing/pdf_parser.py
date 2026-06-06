"""Main PDF parser: dispatch text extraction vs OCR based on PDF type."""
import os
import tempfile
import logging
from pathlib import Path
from typing import Optional, Tuple, List

import fitz  # PyMuPDF

from .text_cleaner import TextCleaner

logger = logging.getLogger(__name__)


class PatentPDFParser:
    """Parse patent PDFs, auto-detecting text vs image-based content.

    Strategy:
    - CN patents: usually have extractable text layers → use PyMuPDF get_text()
    - US patents: mostly scanned images → render page to image → OCR via PaddleOCR
    - Mixed: check each page independently
    """

    # Threshold: minimum chars on a page to consider it "text-based"
    TEXT_THRESHOLD = 50

    def __init__(self, ocr_enabled: bool = True, ocr_use_gpu: bool = False):
        self.ocr_enabled = ocr_enabled
        self.ocr_use_gpu = ocr_use_gpu
        self._ocr_engine = None
        self.cleaner = TextCleaner()

    @property
    def ocr_engine(self):
        if self._ocr_engine is None and self.ocr_enabled:
            from .ocr_engine import OCREngine

            self._ocr_engine = OCREngine(use_gpu=self.ocr_use_gpu)
        return self._ocr_engine

    def parse(self, pdf_path: str) -> dict:
        """Parse a patent PDF and return structured content.

        Args:
            pdf_path: Path to the patent PDF file.

        Returns:
            dict with:
                - 'full_text': Complete extracted text
                - 'pages': List of {page_num, text, is_scanned, images}
                - 'is_scanned': Overall scanned status
                - 'language': Detected language ('zh' or 'en')
                - 'metadata': Patent metadata (title, number, date, etc.)
        """
        doc = fitz.open(pdf_path)
        filename = Path(pdf_path).stem

        # Detect language from filename pattern
        lang = self._detect_language(filename)

        pages = []
        all_text = []
        scanned_count = 0
        image_info = []

        for i, page in enumerate(doc):
            text = page.get_text().strip()
            images = page.get_images()
            is_scanned = len(text) < self.TEXT_THRESHOLD

            if is_scanned:
                scanned_count += 1
                if self.ocr_enabled:
                    text = self._ocr_page(page, i)
                else:
                    text = ""  # OCR disabled, return empty
            else:
                text = self._extract_page_text(page)

            pages.append({
                "page_num": i + 1,
                "text": text,
                "is_scanned": is_scanned,
                "images_count": len(images),
            })
            all_text.append(text)

            if images:
                image_info.extend([{
                    "page": i + 1,
                    "xref": img[0],
                    "width": img[2],
                    "height": img[3],
                } for img in images])

        doc.close()

        full_text = "\n\n".join(all_text)
        full_text = self.cleaner.clean(full_text)

        # Extract metadata
        metadata = self._extract_metadata(pages[0]["text"] if pages else "", lang)

        return {
            "full_text": full_text,
            "pages": pages,
            "page_count": len(pages),
            "scanned_pages": scanned_count,
            "is_scanned": scanned_count > len(pages) / 2,
            "language": lang,
            "metadata": metadata,
            "images": image_info,
        }

    def _detect_language(self, filename: str) -> str:
        """Detect language from filename convention.

        CN patents: CN112310403A, [CN]_sampled_CN...
        US patents: US11088401B1, [US]_sampled_US...
        """
        if "CN" in filename.upper()[:4] or "[CN]" in filename:
            return "zh"
        if "US" in filename.upper()[:4] or "[US]" in filename:
            return "en"
        return "zh"

    def _extract_page_text(self, page: fitz.Page) -> str:
        """Extract text from a text-based page with reading order.

        Handles multi-column layouts by ordering text blocks top-to-bottom,
        left-to-right.
        """
        # Get text blocks with positions
        blocks = page.get_text("blocks")
        text_blocks = [b for b in blocks if b[6] == 0]  # type 0 = text

        if not text_blocks:
            return page.get_text()

        # Sort by y-position (top to bottom), then x (left to right)
        text_blocks.sort(key=lambda b: (round(b[1] / 50) * 50, b[0]))

        lines = []
        for block in text_blocks:
            block_text = block[4].strip()
            if block_text:
                lines.append(block_text)

        return "\n".join(lines)

    def _ocr_page(self, page: fitz.Page, page_num: int) -> str:
        """Run OCR on an image-based page."""
        if self.ocr_engine is None:
            logger.warning(f"OCR disabled, skipping page {page_num + 1}")
            return ""

        # Render page to image at sufficient resolution (300 DPI)
        mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI
        pix = page.get_pixmap(matrix=mat)

        # Save to temporary PNG
        with tempfile.NamedTemporaryFile(
            suffix=".png", delete=False
        ) as tmp:
            pix.save(tmp.name)
            tmp_path = tmp.name

        try:
            if self.ocr_engine.layout_parser:
                result = self.ocr_engine.recognize_with_layout(tmp_path)
                text = result["full_text"]
            else:
                text = self.ocr_engine.recognize(tmp_path)
            return text
        except Exception as e:
            logger.error(f"OCR failed page {page_num + 1}: {e}")
            return ""
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _extract_metadata(self, first_page_text: str, lang: str) -> dict:
        """Extract patent metadata from the first page text.

        CN patent first page typically contains:
        - (19) 中华人民共和国国家知识产权局
        - (12) 发明专利申请
        - (21) 申请号 ...
        - (22) 申请日 ...
        - (71) 申请人 ...
        - (54) 发明名称 ...

        US patent: varies by format.
        """
        import re

        metadata = {
            "title": "",
            "application_number": "",
            "application_date": "",
            "applicant": "",
            "inventors": "",
            "ipc_classification": "",
        }

        if lang == "zh":
            # CN patent metadata extraction
            m = re.search(r"申请号\s*(\S+)", first_page_text)
            if m:
                metadata["application_number"] = m.group(1)
            m = re.search(r"申请日\s*(\S+)", first_page_text)
            if m:
                metadata["application_date"] = m.group(1)
            m = re.search(r"申请人\s*(.+?)(?:\n|地址)", first_page_text)
            if m:
                metadata["applicant"] = m.group(1).strip()
            m = re.search(r"发明人\s*(.+?)(?:\n|专利)", first_page_text)
            if m:
                metadata["inventors"] = m.group(1).strip()
            m = re.search(r"发明名称\s*(.+?)(?:\n)", first_page_text)
            if m:
                metadata["title"] = m.group(1).strip()
        else:
            # US patent metadata extraction (from OCR text - more variable)
            m = re.search(
                r"Appl\.?\s*No\.?:?\s*([\d,/]+)", first_page_text,
                re.IGNORECASE,
            )
            if m:
                metadata["application_number"] = m.group(1)
            m = re.search(
                r"(?:Title|TITLE)[:\s]+(.+?)(?:\n)", first_page_text,
                re.IGNORECASE,
            )
            if m:
                metadata["title"] = m.group(1).strip()

        return metadata

    def parse_directory(
        self, directory: str, limit: int = 0
    ) -> List[dict]:
        """Parse all PDFs in a directory.

        Args:
            directory: Path to directory containing PDF files.
            limit: Max files to parse (0 = all).

        Returns:
            List of parse result dicts.
        """
        results = []
        pdf_files = sorted(
            f for f in os.listdir(directory) if f.lower().endswith(".pdf")
        )
        if limit:
            pdf_files = pdf_files[:limit]

        for i, filename in enumerate(pdf_files):
            pdf_path = os.path.join(directory, filename)
            logger.info(f"[{i+1}/{len(pdf_files)}] Parsing {filename}")
            try:
                result = self.parse(pdf_path)
                result["filename"] = filename
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to parse {filename}: {e}")
                continue

        return results
