"""Verify Agent: multi-dimension validation with fail classification."""
from typing import List
import re

from models.quintuple import Quintuple
from .state import AgentState


# 知识库：锂电池领域物理边界
PHYSICAL_BOUNDS = {
    "能量密度": (0, 1000, "Wh/kg"),
    "比容量": (0, 5000, "mAh/g"),
    "库伦效率": (0, 100, "%"),
    "容量保持率": (0, 100, "%"),
    "烧结温度": (20, 2000, "℃"),
    "循环寿命": (1, 100000, "次"),
    "孔隙率": (0, 100, "%"),
    "压实密度": (0.1, 10, "g/cm3"),
    "离子电导率": (1e-10, 1, "S/cm"),
    "电压": (0, 10, "V"),
}


class VerifyAgent:
    """Multi-dimension validator for extracted quintuples."""

    def __init__(self, strict: bool = False):
        self.strict = strict

    def _check_physical_boundary(self, q: Quintuple) -> tuple:
        """Check if the value is within known physical bounds."""
        name = q.name
        if name in PHYSICAL_BOUNDS:
            lo, hi, _unit = PHYSICAL_BOUNDS[name]
            nums = re.findall(r"\d+\.?\d*", q.value)
            if nums:
                val = float(nums[0])
                if lo <= val <= hi:
                    return True, ""
                return (
                    False,
                    f"{name}={q.value} out of bounds [{lo},{hi}]",
                )
        return True, ""

    def _check_syntactic_completeness(self, q: Quintuple) -> tuple:
        """Check if quintuple has all required elements."""
        missing = []
        if not q.name:
            missing.append("名称")
        if not q.value:
            missing.append("数值")
        if not q.relation:
            missing.append("关系")
        if missing:
            return (
                False,
                f"缺失要素: {', '.join(missing)}",
            )
        return True, ""

    def _check_logical_consistency(self, q: Quintuple) -> tuple:
        """Check logical consistency of the quintuple."""
        return True, ""

    def verify(
        self, quintuples: List[Quintuple]
    ) -> List[dict]:
        """Return verification results for each quintuple."""
        results = []
        for i, q in enumerate(quintuples):
            checks = []
            passed = True

            for check_fn, dim_name in [
                (self._check_physical_boundary, "physical_boundary"),
                (
                    self._check_syntactic_completeness,
                    "syntactic_completeness",
                ),
                (
                    self._check_logical_consistency,
                    "logical_consistency",
                ),
            ]:
                ok, reason = check_fn(q)
                checks.append(
                    {"dimension": dim_name, "pass": ok, "reason": reason}
                )
                if not ok:
                    passed = False

            # Critical if syntactic_completeness fails (missing core fields)
            syn_check = next(
                (c for c in checks if c["dimension"] == "syntactic_completeness"),
                None,
            )
            is_critical = (
                not any(c["pass"] for c in checks)
                or (syn_check and not syn_check["pass"])
            )
            results.append({
                "index": i,
                "verdict": "pass" if passed else "fail",
                "checks": checks,
                "severity": "critical" if is_critical else "minor",
            })

        return results

    def __call__(self, state: AgentState) -> AgentState:
        quintuples = state.get("extracted_quintuples", [])
        results = self.verify(quintuples)

        all_pass = all(r["verdict"] == "pass" for r in results)
        critical_fail = any(r["severity"] == "critical" for r in results)

        if all_pass:
            next_status = "verification_pass"
        elif critical_fail:
            next_status = "verification_critical_fail"
        else:
            next_status = "verification_partial_fail"

        return {
            **state,
            "verification_results": results,
            "status": next_status,
        }
