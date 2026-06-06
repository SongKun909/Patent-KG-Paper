"""Ontology model for technical indicator knowledge graph."""

# Entity types
ENTITY_TYPES = {
    "Patent": "专利",
    "TechnicalIndicator": "技术指标",
    "IndicatorName": "指标名称",
    "IndicatorValue": "指标数值",
    "IndicatorRelation": "指标关系",
    "IndicatorObject": "指标对象",
    "ExperimentalCondition": "实验条件",
}

# Relation types
RELATION_TYPES = {
    "HAS_INDICATOR": "包含指标",
    "HAS_NAME": "拥有名称",
    "HAS_VALUE": "拥有数值",
    "HAS_RELATION": "拥有关系",
    "HAS_OBJECT": "作用对象",
    "HAS_CONDITION": "实验条件",
    "CORRELATED_WITH": "指标关联",
    "BELONGS_TO_CATEGORY": "归属类别",
    "CITES": "引用专利",
}

# Indicator categories for classification
INDICATOR_CATEGORIES = {
    "电化学性能": [
        "比容量", "能量密度", "功率密度", "循环寿命", "库伦效率",
        "倍率性能", "容量保持率", "首次放电比容量", "首次充电比容量",
        "放电容量", "充电容量", "不可逆容量",
    ],
    "物理特性": [
        "压实密度", "振实密度", "比表面积", "粒度", "粒径",
        "厚度", "孔隙率", "密度",
    ],
    "热力学": [
        "热稳定性", "分解温度", "熔点", "玻璃化转变温度",
    ],
    "力学性能": [
        "抗拉强度", "断裂伸长率", "弹性模量", "硬度",
    ],
    "工艺参数": [
        "烧结温度", "保温时间", "升温速率", "降温速率",
        "质量分数", "摩尔分数", "浓度", "粘度", "固含量",
    ],
    "电学特性": [
        "电导率", "离子电导率", "电子电导率", "电化学窗口",
        "电压平台", "开路电压", "工作电压", "截止电压",
        "界面阻抗", "阻抗", "扩散系数", "迁移数",
    ],
}


def classify_indicator(name: str) -> str:
    """Classify an indicator name into a category."""
    for category, indicators in INDICATOR_CATEGORIES.items():
        for kw in indicators:
            if kw in name:
                return category
    return "其他"


# JSON-LD context for semantic web compatibility
JSONLD_CONTEXT = {
    "@context": {
        "schema": "http://schema.org/",
        "patent": "http://example.org/patent/",
        "indicator": "http://example.org/indicator/",
        "name": "schema:name",
        "value": "schema:value",
        "unitCode": "schema:unitCode",
        "relation": "patent:relation",
        "object": "patent:object",
        "condition": "patent:condition",
        "category": "patent:category",
    }
}
