"""Rule-based baseline: regex + keyword matching for quintuple extraction.

This serves as Experiment 2a — the traditional IE approach without ML/LLM.
"""
import re
from typing import List


class RuleBaseline:
    """Extract quintuples using purely regex and keyword rules."""

    # Pattern: name + relation_word + value + unit
    # Keywords list shared across patterns
    ZH_KEYWORDS = (
        r"比容量|能量密度|功率密度|循环寿命|库伦效率|库仑效率"
        r"|效率|容量保持率|压实密度|振实密度|比表面积"
        r"|粒度|粒径|厚度|孔隙率|电导率|离子电导率|电子电导率"
        r"|热稳定性|分解温度|熔点|硬度|电压|容量|放电容量|充电容量"
        r"|烧结温度|保温时间|升温速率|降温速率|质量分数|摩尔分数"
        r"|浓度|粘度|固含量|pH|密度|电化学窗口"
        r"|首效|首次效率|标称电压|标称容量|额定容量|阻抗"
        r"|扩散系数|迁移数|倍率|充放电倍率|放电比容量|充电比容量"
        r"|首次放电比容量|首次充电比容量|首次库伦效率|首次放电容量"
    )

    EN_KEYWORDS = (
        r"specific capacity|energy density|power density"
        r"|cycle life|coulombic efficiency|capacity retention"
        r"|tap density|specific surface area|ionic conductivity"
        r"|electrochemical window|discharge capacity|charge capacity"
        r"|thermal stability|tensile strength|elastic modulus|porosity"
        r"|particle size|voltage plateau"
        r"|initial discharge capacity|initial coulombic efficiency"
    )

    RELATION_WORDS = (
        r"达到|为|是|等于|提升至|提高至|降低至"
        r"|超过|优于|高达|低至|约|大约|不小于|不大于|大于|小于|范围为"
        r"|of|is|was|reached|achieved|at|about|approximately"
    )

    EXTRACTION_PATTERNS = [
        # Chinese pattern
        re.compile(
            r"(?P<name>" + ZH_KEYWORDS + r")"
            r"\s*(?P<relation>" + RELATION_WORDS + r")\s*"
            r"(?P<value>\d+\.?\d*\s*(?:~|～|-|至)\s*\d+\.?\d*\s*[^\s,，。.、；;]*"
            r"|\d+\.?\d*\s*[^\s,，。.、；;]*)"
        ),
        # English pattern
        re.compile(
            r"(?P<name>" + EN_KEYWORDS + r")"
            r"\s*(?P<relation>" + RELATION_WORDS + r")\s+"
            r"(?P<value>\d+\.?\d*\s*(?:~|to|-)\s*\d+\.?\d*\s*[^\s,;.]*"
            r"|\d+\.?\d*\s*[^\s,;.]*)",
            re.IGNORECASE,
        ),
    ]

    # Object detection patterns
    OBJECT_PATTERNS = re.compile(
        r"(正极|负极|隔膜|电解液|电池|电芯|集流体|粘结剂|导电剂"
        r"|阴极|阳极|cathode|anode|separator|electrolyte"
        r"|battery|cell|electrode)"
    )

    # Condition patterns
    CONDITION_PATTERNS = re.compile(
        r"(\d+\.?\d*\s*C\b|\d+\.?\d*\s*℃|\d+\.?\d*\s*°C"
        r"|\d+\.?\d*\s*mA/g|\d+\.?\d*\s*mA\.g"
        r"|\d+\.?\d*\s*kPa|\d+\.?\d*\s*MPa"
        r"|恒流|恒压|倍率|截止电压|室温|高温|低温"
        r"|constant current|constant voltage|room temperature)"
    )

    def extract(self, text: str) -> List[dict]:
        """Extract quintuples from patent text using rule matching.

        Returns:
            List of dicts with keys: 指标名称, 指标数值, 指标关系,
            指标对象, 实验条件
        """
        results = []

        for pattern in self.EXTRACTION_PATTERNS:
            for match in pattern.finditer(text):
                name = match.group("name")
                relation = match.group("relation")
                value = match.group("value")

                # Clean up relation
                relation = re.sub(r"[~:：\s]", "", relation)
                if not relation:
                    relation = "等于"

                # Find object near the match
                obj = self._find_object(text, match.start(), match.end())

                # Find condition near the match
                condition = self._find_condition(
                    text, match.start(), match.end()
                )

                results.append({
                    "指标名称": name,
                    "指标数值": value.strip(),
                    "指标关系": relation,
                    "指标对象": obj,
                    "实验条件": condition,
                })

        return results

    def _find_object(self, text: str, start: int, end: int) -> str:
        """Find indicator object near the matched span."""
        # Search in ±100 chars window
        window_start = max(0, start - 100)
        window_end = min(len(text), end + 100)
        window = text[window_start:window_end]

        matches = self.OBJECT_PATTERNS.findall(window)
        if matches:
            # Return closest match
            return matches[0]
        return "电池"

    def _find_condition(
        self, text: str, start: int, end: int
    ) -> str:
        """Find experimental condition near the matched span."""
        window_start = max(0, start - 200)
        window_end = min(len(text), end + 200)
        window = text[window_start:window_end]

        matches = self.CONDITION_PATTERNS.findall(window)
        if matches:
            return ", ".join(matches[:3])
        return "无"
