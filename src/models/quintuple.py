"""Core data models for technical indicator extraction."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Quintuple:
    """A single extracted technical indicator quintuple."""
    name: str          # 指标名称
    value: str         # 指标数值
    relation: str      # 指标关系
    object: str        # 指标对象
    condition: str     # 实验条件
    source_text: str = ""   # 原文片段
    confidence: float = 1.0  # LLM 置信度

    def to_dict(self) -> dict:
        return {
            "指标名称": self.name,
            "指标数值": self.value,
            "指标关系": self.relation,
            "指标对象": self.object,
            "实验条件": self.condition,
        }

    @classmethod
    def from_dict(cls, d: dict, source_text: str = "",
                  confidence: float = 1.0) -> "Quintuple":
        return cls(
            name=d.get("指标名称", ""),
            value=d.get("指标数值", ""),
            relation=d.get("指标关系", ""),
            object=d.get("指标对象", ""),
            condition=d.get("实验条件", ""),
            source_text=source_text,
            confidence=confidence,
        )


@dataclass
class IndicatorSentence:
    """A sentence identified as potentially containing indicators."""
    text: str
    lang: str = "zh"  # "zh" or "en"
    patent_id: str = ""
    section: str = ""  # 所属章节
    dep_parse: Optional[dict] = None  # Stanza 依存解析结果

    def __hash__(self):
        return hash((self.text, self.patent_id))
