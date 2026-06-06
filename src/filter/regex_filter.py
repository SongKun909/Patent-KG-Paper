"""Layer 1: Regex-based indicator sentence filter."""
import re
from typing import List


class RegexIndicatorFilter:
    """Fast regex filter to identify sentences likely containing
    technical indicators."""

    # 数值+单位模式
    NUMBER_UNIT_PATTERNS = [
        r"\d+\.?\d*\s*(Wh/kg|mAh/g|mAh\.g|Wh\.kg|kW/kg|W/kg)",
        r"\d+\.?\d*\s*(℃|°C|°F|K\b)",
        r"\d+\.?\d*\s*(nm|μm|mm|cm|m\b)",
        r"\d+\.?\d*\s*(MPa|GPa|kPa|Pa\b)",
        r"\d+\.?\d*\s*(S/cm|S\.cm|S/m)",
        r"\d+\.?\d*\s*(mol/L|mol\.L|M\b)",
        r"\d+\.?\d*\s*(g/cm3|g\.cm|kg/m3)",
        r"\d+\.?\d*\s*(h\b|min\b|s\b|小时|分钟|秒)",
        r"\d+\.?\d*\s*%",
        r"\d+\.?\d*\s*(V\b|mV|kV)",
        r"\d+\.?\d*\s*(A\b|mA)",
        r"\d+\.?\d*\s*(C\b)",  # 倍率
        r"\d+\.?\d*\s*(wt\s*%|wt\.?%)",
    ]

    # 数值+范围模式
    RANGE_PATTERNS = [
        r"\d+\.?\d*\s*[-~〜]\s*\d+\.?\d*\s*(℃|°C|h|min|V|MPa|nm|%)",
        r"\d+\.?\d*\s*(至|到)\s*\d+\.?\d*",
    ]

    # 指标关键词 (中文)
    ZH_KEYWORDS = [
        "比容量", "能量密度", "功率密度", "循环寿命", "循环",
        "库伦效率", "库仑效率", "倍率", "极化", "阻抗",
        "扩散系数", "放电比容量", "充电比容量", "首次",
        "容量保持", "容量保持率", "压实密度", "振实密度",
        "比表面积", "粒度", "粒径", "厚度", "孔隙率",
        "电导率", "离子电导", "电子电导", "迁移数",
        "热稳定性", "分解温度", "熔点", "玻璃化转变",
        "抗拉强度", "断裂伸长", "弹性模量", "硬度",
        "电压平台", "开路电压", "工作电压", "截止电压",
        "放电容量", "充电容量", "不可逆容量", "可逆容量",
        "烧结温度", "保温时间", "升温速率", "降温速率",
        "质量分数", "摩尔分数", "体积分数", "浓度",
        "粘度", "固含量", "pH", "密度", "电化学窗口",
        "首效", "首次效率", "首次库伦效率", "标称电压",
        "标称容量", "额定容量", "能量效率", "功率",
        "锂离子迁移数", "锂离子扩散系数", "界面阻抗",
    ]

    # 指标关键词 (英文)
    EN_KEYWORDS = [
        "specific capacity", "energy density", "power density",
        "cycle life", "coulombic efficiency", "rate capability",
        "capacity retention", "tap density", "specific surface area",
        "ionic conductivity", "electrochemical window",
        "discharge capacity", "charge capacity", "thermal stability",
        "tensile strength", "elastic modulus", "porosity",
        "particle size", "voltage plateau", "open circuit voltage",
    ]

    # 比较/关系关键词
    RELATION_KEYWORDS = [
        "达到", "提升至", "提高至", "降低至", "超过", "优于",
        "高达", "低至", "仅为", "不小于", "不大于",
        "achieve", "reach", "increase", "decrease",
        "higher than", "lower than", "at least", "at most",
    ]

    def __init__(self):
        self.num_unit_re = re.compile(
            "|".join(self.NUMBER_UNIT_PATTERNS), re.IGNORECASE
        )
        self.range_re = re.compile(
            "|".join(self.RANGE_PATTERNS), re.IGNORECASE
        )
        self.keyword_re = re.compile(
            "|".join(self.ZH_KEYWORDS + self.EN_KEYWORDS),
            re.IGNORECASE,
        )
        self.relation_re = re.compile(
            "|".join(self.RELATION_KEYWORDS), re.IGNORECASE
        )

    def _is_indicator_candidate(self, sentence: str) -> bool:
        """Check if a sentence is likely to contain a technical indicator."""
        if self.num_unit_re.search(sentence):
            return True
        if self.range_re.search(sentence):
            return True
        # keyword + relation co-occurrence
        if self.keyword_re.search(sentence) and (
            self.relation_re.search(sentence)
            or self.num_unit_re.search(sentence)
        ):
            return True
        # keyword + number
        if self.keyword_re.search(sentence) and re.search(
            r"\d+\.?\d*", sentence
        ):
            return True
        return False

    def filter(self, sentences: List[str]) -> List[str]:
        """Return only sentences that are indicator candidates."""
        return [s for s in sentences if self._is_indicator_candidate(s)]

    def filter_with_indices(
        self, sentences: List[str]
    ) -> List[tuple]:
        """Return (index, sentence) for indicator candidates."""
        return [
            (i, s)
            for i, s in enumerate(sentences)
            if self._is_indicator_candidate(s)
        ]
