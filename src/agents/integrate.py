"""Integrate Agent: term normalization, conflict resolution, dedup."""
from typing import List

from models.quintuple import Quintuple
from .state import AgentState


# 术语归一化映射表
TERM_NORMALIZATION = {
    "首次放电比容量": "首次放电比容量",
    "首次放电容量": "首次放电比容量",
    "首圈放电比容量": "首次放电比容量",
    "initial discharge capacity": "首次放电比容量",
    "比容量": "比容量",
    "specific capacity": "比容量",
    "能量密度": "能量密度",
    "energy density": "能量密度",
    "循环寿命": "循环寿命",
    "cycle life": "循环寿命",
    "库伦效率": "库伦效率",
    "库仑效率": "库伦效率",
    "coulombic efficiency": "库伦效率",
}


class IntegrateAgent:
    """Integrates multiple extraction results into final output."""

    def __init__(self, llm=None):
        self.llm = llm

    def normalize_term(self, term: str) -> str:
        """Map variant terms to canonical forms."""
        return TERM_NORMALIZATION.get(term, term)

    def _is_duplicate(self, q1: Quintuple, q2: Quintuple) -> bool:
        """Check if two quintuples refer to the same indicator."""
        score = 0
        if q1.name == q2.name:
            score += 1
        if q1.object == q2.object:
            score += 1
        if q1.value == q2.value:
            score += 1
        if q1.condition == q2.condition:
            score += 0.5
        return score >= 2

    def integrate(
        self,
        quintuples: List[Quintuple],
        verification_results: List[dict] = None,
    ) -> List[Quintuple]:
        """Integrate verified quintuples into final output."""
        if verification_results:
            failed_indices = {
                r["index"]
                for r in verification_results
                if r["verdict"] == "fail" and r["severity"] == "critical"
            }
            quintuples = [
                q
                for i, q in enumerate(quintuples)
                if i not in failed_indices
            ]

        for q in quintuples:
            q.name = self.normalize_term(q.name)
            q.object = self.normalize_term(q.object)

        final = []
        for q in quintuples:
            if not any(self._is_duplicate(q, f) for f in final):
                final.append(q)

        return final

    def __call__(self, state: AgentState) -> AgentState:
        quintuples = state.get("extracted_quintuples", [])
        verification = state.get("verification_results", [])
        final = self.integrate(quintuples, verification)
        return {
            **state,
            "final_quintuples": final,
            "status": "done",
        }
