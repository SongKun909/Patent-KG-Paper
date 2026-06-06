"""Extract Agent: syntactic-augmented extraction."""
from typing import List

from models.quintuple import Quintuple, IndicatorSentence
from llm.base import BaseLLM
from .state import AgentState


class ExtractAgent:
    """Extracts quintuples from indicator sentences with syntactic hints."""

    def __init__(self, llm: BaseLLM):
        self.llm = llm

    def extract_from_sentence(
        self, sentence: IndicatorSentence
    ) -> List[Quintuple]:
        """Extract quintuples from a single indicator sentence."""
        syntactic_hints = sentence.dep_parse
        return self.llm.extract_quintuples(
            sentence.text, syntactic_hints
        )

    def extract_batch(
        self, sentences: List[IndicatorSentence]
    ) -> List[Quintuple]:
        """Extract from all candidate sentences, deduplicate."""
        all_quintuples = []
        for sent in sentences:
            quints = self.extract_from_sentence(sent)
            for q in quints:
                q.source_text = sent.text
            all_quintuples.extend(quints)
        return all_quintuples

    def __call__(self, state: AgentState) -> AgentState:
        sentences = state.get("sentences", [])
        quintuples = self.extract_batch(sentences)
        return {
            **state,
            "extracted_quintuples": quintuples,
            "status": "extracting_done",
        }
