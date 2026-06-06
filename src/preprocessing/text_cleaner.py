"""Text post-processing: clean extracted/OCR'd patent text."""
import re
from typing import List


class TextCleaner:
    """Clean and normalize patent text extracted from PDF or OCR."""

    # Chinese patent header pattern
    CN_HEADER_PATTERNS = [
        re.compile(r"权利要求书\s*\d+/\d+\s*页"),
        re.compile(r"说明书\s*\d+/\d+\s*页"),
        re.compile(r"说明书摘要"),
        re.compile(r"附图\s*\d+/\d+\s*页"),
        re.compile(r"SO50297"),
    ]

    # Page number / header patterns
    PAGE_PATTERNS = [
        re.compile(r"^\s*\d+\s*$"),  # Standalone page number
        re.compile(r"^\s*第\s*\d+\s*页\s*$"),
        re.compile(r"^Page\s+\d+\s*$", re.IGNORECASE),
    ]

    @staticmethod
    def remove_headers_footers(text: str) -> str:
        """Remove patent document headers and footers."""
        for pattern in TextCleaner.CN_HEADER_PATTERNS:
            text = pattern.sub("", text)
        return text

    @staticmethod
    def remove_page_numbers(lines: List[str]) -> List[str]:
        """Filter out standalone page number lines."""
        return [
            line
            for line in lines
            if not any(
                p.match(line.strip()) for p in TextCleaner.PAGE_PATTERNS
            )
        ]

    @staticmethod
    def merge_hyphenated_english(text: str) -> str:
        """Merge hyphenated words split across lines in English text.

        Example: 'electro-\nde' -> 'electrode'
        """
        return re.sub(r"([a-z])-\s*\n\s*([a-z])", r"\1\2", text)

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace: collapse multiple spaces and newlines."""
        # Collapse 3+ newlines to 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Collapse multiple spaces
        text = re.sub(r" {2,}", " ", text)
        # Remove trailing spaces on lines
        text = re.sub(r" +\n", "\n", text)
        return text.strip()

    @staticmethod
    def split_into_paragraphs(text: str) -> List[str]:
        """Split cleaned text into paragraphs."""
        paras = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paras if len(p.strip()) > 20]

    @staticmethod
    def split_into_sentences(paragraph: str, lang: str = "zh") -> List[str]:
        """Split a paragraph into sentences based on language."""
        if lang.startswith("zh"):
            # Chinese sentence boundary: 。！？ but not ., etc.
            sentences = re.split(r"(?<=[。！？])\s*", paragraph)
        else:
            # English: . ! ? followed by space and capital letter
            sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", paragraph)
        return [s.strip() for s in sentences if len(s.strip()) > 3]

    def clean(self, text: str) -> str:
        """Full cleaning pipeline."""
        text = self.remove_headers_footers(text)
        text = self.merge_hyphenated_english(text)
        text = self.normalize_whitespace(text)
        return text
