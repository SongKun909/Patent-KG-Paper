"""LangGraph state definition for the multi-agent pipeline."""
from typing import Annotated, List
import operator

try:
    from langgraph.graph.message import add_messages
except ImportError:
    add_messages = operator.add  # fallback

from typing_extensions import TypedDict

from models.quintuple import Quintuple, IndicatorSentence


class AgentState(TypedDict):
    """Shared state across Extract-Verify-Integrate agents."""

    sentences: List[IndicatorSentence]
    extracted_quintuples: List[Quintuple]
    verification_results: List[dict]
    final_quintuples: List[Quintuple]
    retry_count: int
    errors: Annotated[List[str], operator.add]
    status: str  # "extracting" | "verifying" | "integrating" | "done"
    messages: Annotated[list, add_messages]
