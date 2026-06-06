"""Tests for rule-based extraction baseline."""
import pytest
from baselines.rule_baseline import RuleBaseline


class TestRuleBaseline:
    @pytest.fixture
    def baseline(self):
        return RuleBaseline()

    def test_extract_chinese_indicator(self, baseline):
        text = "电池的能量密度达到300Wh/kg，循环寿命超过2000次。"
        results = baseline.extract(text)
        assert len(results) > 0
        assert any(r["指标名称"] == "能量密度" for r in results)

    def test_extract_multiple_indicators(self, baseline):
        text = (
            "正极材料的比容量为150mAh/g，"
            "压实密度达到2.5g/cm3，"
            "烧结温度为700℃。"
        )
        results = baseline.extract(text)
        assert len(results) >= 2

    def test_extract_english_indicator(self, baseline):
        text = "The energy density reached 300 Wh/kg at 0.5C rate."
        results = baseline.extract(text)
        assert len(results) > 0

    def test_extract_no_indicator(self, baseline):
        text = "本发明提供了一种制备方法，包括以下步骤。"
        results = baseline.extract(text)
        assert len(results) == 0

    def test_quintuple_format(self, baseline):
        text = "能量密度达到300Wh/kg。"
        results = baseline.extract(text)
        assert len(results) > 0
        r = results[0]
        assert "指标名称" in r
        assert "指标数值" in r
        assert "指标关系" in r
        assert "指标对象" in r
        assert "实验条件" in r
