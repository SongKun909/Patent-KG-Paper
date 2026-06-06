"""LangGraph state machine for Extract-Verify-Integrate pipeline."""
from typing import Literal

from langgraph.graph import StateGraph, END

from .state import AgentState
from .extract import ExtractAgent
from .verify import VerifyAgent
from .integrate import IntegrateAgent
from llm.base import BaseLLM


def build_pipeline_graph(
    llm: BaseLLM,
    max_retries: int = 2,
) -> StateGraph:
    """Build the LangGraph E-V-I pipeline."""

    extract_agent = ExtractAgent(llm)
    verify_agent = VerifyAgent()
    integrate_agent = IntegrateAgent(llm)

    graph = StateGraph(AgentState)

    graph.add_node("extract", extract_agent)
    graph.add_node("verify", verify_agent)
    graph.add_node("integrate", integrate_agent)

    graph.set_entry_point("extract")
    graph.add_edge("extract", "verify")

    graph.add_conditional_edges(
        "verify",
        _route_after_verify,
        {
            "integrate": "integrate",
            "retry_extract": "extract",
            "end_noise": END,
        },
    )

    graph.add_edge("integrate", END)

    return graph.compile()


def _route_after_verify(
    state: AgentState,
) -> Literal["integrate", "retry_extract", "end_noise"]:
    """Route based on verification results."""
    status = state.get("status", "")
    retry_count = state.get("retry_count", 0)

    if status == "verification_pass":
        return "integrate"
    elif status == "verification_partial_fail" and retry_count < 2:
        return "retry_extract"
    elif status == "verification_critical_fail":
        return "end_noise"
    else:
        return "integrate"
