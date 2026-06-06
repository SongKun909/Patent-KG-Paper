"""Tests for core data models."""
from models.quintuple import Quintuple, IndicatorSentence


class TestQuintuple:
    def test_from_dict_basic(self, sample_quintuple_dict):
        q = Quintuple.from_dict(sample_quintuple_dict)
        assert q.name == "能量密度"
        assert q.value == "300Wh/kg"
        assert q.relation == "等于"
        assert q.object == "锂离子电池"
        assert q.condition == "0.5C倍率下"

    def test_to_dict_roundtrip(self, sample_quintuple_dict):
        q = Quintuple.from_dict(sample_quintuple_dict)
        assert q.to_dict() == sample_quintuple_dict

    def test_default_values(self):
        q = Quintuple.from_dict({"指标名称": "容量"})
        assert q.value == ""
        assert q.confidence == 1.0

    def test_with_confidence(self):
        q = Quintuple.from_dict(
            {"指标名称": "比容量", "指标数值": "150mAh/g"},
            confidence=0.85
        )
        assert q.confidence == 0.85


class TestIndicatorSentence:
    def test_creation(self):
        s = IndicatorSentence(
            text="能量密度达到300Wh/kg",
            lang="zh",
            patent_id="CN123456",
        )
        assert s.lang == "zh"
        assert s.patent_id == "CN123456"
        assert s.dep_parse is None

    def test_hash_equality(self):
        s1 = IndicatorSentence(text="test", patent_id="P1")
        s2 = IndicatorSentence(text="test", patent_id="P1")
        assert hash(s1) == hash(s2)
