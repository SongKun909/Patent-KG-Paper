"""Main pipeline orchestrating the full extraction workflow."""
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


class ExtractionPipeline:
    """Complete three-layer funnel → multi-agent extraction pipeline."""

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

    def evaluate(
        self,
        pred_quintuples: List[Quintuple],
        gold_quintuples: List[dict],
    ) -> F1StarResult:
        """Evaluate extraction against gold standard."""
        pred_dicts = [q.to_dict() for q in pred_quintuples]
        return compute_f1_star(pred_dicts, gold_quintuples)
