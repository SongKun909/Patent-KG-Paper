"""Main pipeline orchestrating the full extraction workflow."""
import logging
from pathlib import Path
from typing import List, Optional

from config import PipelineConfig, load_config
from llm.deepseek import DeepSeekLLM
from filter.regex_filter import RegexIndicatorFilter
from syntax.parser import StanzaParser
from syntax.mapping import UDToQuintupleMapper
from agents.graph import build_pipeline_graph
from agents.state import AgentState
from models.quintuple import IndicatorSentence, Quintuple
from eval.f1_star import compute_f1_star, F1StarResult

logger = logging.getLogger(__name__)


class ExtractionPipeline:
    """Complete PDF→three-layer funnel→multi-agent extraction pipeline."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or load_config()
        self.llm = DeepSeekLLM(
            api_key=self.config.llm.api_key,
            base_url=self.config.llm.base_url,
            model=self.config.llm.model,
            temperature=self.config.llm.temperature,
        )
        self.regex_filter = RegexIndicatorFilter()
        self.parser_zh = StanzaParser("zh")
        self.parser_en = StanzaParser("en")
        self.mapper = UDToQuintupleMapper()
        self.graph = build_pipeline_graph(self.llm)
        self._classifier = None  # Lazy load Layer 2
        self._pdf_parser = None  # Lazy load PDF parser

    def filter_sentences(self, text: str, lang: str = "zh"):
        """Layer 1: Regex-based filtering."""
        import re

        sep = r"[。.；;\n]"
        sentences = [
            s.strip()
            for s in re.split(sep, text)
            if len(s.strip()) > 5
        ]
        return self.regex_filter.filter(sentences)

    def parse_syntax(
        self, sentences: list, lang: str = "zh"
    ) -> list:
        """Layer 3: Dependency parsing."""
        parser = self.parser_zh if lang.startswith("zh") else self.parser_en
        results = []
        for s in sentences:
            parse = parser.parse(s)
            hints = self.mapper.map_to_hints(parse.get("dependencies", []))
            results.append(hints)
        return results

    def run(
        self, text: str, lang: str = "zh", patent_id: str = ""
    ) -> List[Quintuple]:
        """Run complete pipeline on a single patent text."""
        candidate_sentences = self.filter_sentences(text, lang)
        if not candidate_sentences:
            return []

        parses = self.parse_syntax(candidate_sentences, lang)

        indicator_sentences = []
        for sent, parse_hints in zip(candidate_sentences, parses):
            ind_sent = IndicatorSentence(
                text=sent,
                lang=lang,
                patent_id=patent_id,
                dep_parse=parse_hints,
            )
            indicator_sentences.append(ind_sent)

        initial_state: AgentState = {
            "sentences": indicator_sentences,
            "extracted_quintuples": [],
            "verification_results": [],
            "final_quintuples": [],
            "retry_count": 0,
            "errors": [],
            "status": "extracting",
            "messages": [],
        }

        result = self.graph.invoke(initial_state)
        return result.get("final_quintuples", [])

    @property
    def pdf_parser(self):
        if self._pdf_parser is None:
            from preprocessing.pdf_parser import PatentPDFParser

            self._pdf_parser = PatentPDFParser(ocr_enabled=True)
        return self._pdf_parser

    def run_from_pdf(
        self, pdf_path: str
    ) -> List[Quintuple]:
        """Run full pipeline from a patent PDF file.

        Args:
            pdf_path: Path to a patent PDF file (CN or US).

        Returns:
            List of extracted Quintuple objects.
        """
        if not Path(pdf_path).exists():
            logger.error(f"PDF not found: {pdf_path}")
            return []

        # Step 0: Parse PDF → full text
        logger.info(f"Parsing PDF: {pdf_path}")
        parsed = self.pdf_parser.parse(pdf_path)
        text = parsed["full_text"]
        lang = parsed["language"]

        if not text:
            logger.warning(f"No text extracted from {pdf_path}")
            return []

        filename = Path(pdf_path).stem
        patent_id = parsed["metadata"].get("application_number", filename)

        logger.info(
            f"Extracted {len(text)} chars from {parsed['page_count']} pages "
            f"({parsed['scanned_pages']} scanned), lang={lang}"
        )

        return self.run(text, lang, patent_id)

    def run_batch_from_directory(
        self, directory: str, limit: int = 0
    ) -> List[dict]:
        """Run pipeline on all PDFs in a directory.

        Returns:
            List of {filename, metadata, quintuples} dicts.
        """
        import os

        results = []
        pdf_files = sorted(
            f for f in os.listdir(directory) if f.lower().endswith(".pdf")
        )
        if limit:
            pdf_files = pdf_files[:limit]

        for i, filename in enumerate(pdf_files):
            pdf_path = os.path.join(directory, filename)
            logger.info(f"[{i+1}/{len(pdf_files)}] Processing {filename}")
            try:
                quints = self.run_from_pdf(pdf_path)
                results.append({
                    "filename": filename,
                    "quintuples": [q.to_dict() for q in quints],
                    "count": len(quints),
                })
            except Exception as e:
                logger.error(f"Failed {filename}: {e}")
                results.append({
                    "filename": filename,
                    "quintuples": [],
                    "count": 0,
                    "error": str(e),
                })

        return results

    def evaluate(
        self,
        pred_quintuples: List[Quintuple],
        gold_quintuples: List[dict],
    ) -> F1StarResult:
        """Evaluate extraction against gold standard."""
        pred_dicts = [q.to_dict() for q in pred_quintuples]
        return compute_f1_star(pred_dicts, gold_quintuples)
