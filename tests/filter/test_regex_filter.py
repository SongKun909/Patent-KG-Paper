"""Tests for regex filter."""
import pytest
import re
from filter.regex_filter import RegexIndicatorFilter


class TestRegexFilter:
    @pytest.fixture
    def filter_obj(self):
        return RegexIndicatorFilter()

    def test_detect_number_with_unit(self, filter_obj):
        sentences = [
            "能量密度达到300Wh/kg，性能优异。",
            "本发明提供一种制备方法。",
        ]
        result = filter_obj.filter(sentences)
        assert len(result) == 1
        assert "300Wh/kg" in result[0]

    def test_detect_temperature_range(self, filter_obj):
        sentences = [
            "烧结温度为700~800℃。",
            "将材料混合均匀。",
        ]
        result = filter_obj.filter(sentences)
        assert len(result) == 1
        assert "700~800℃" in result[0]

    def test_detect_indicator_keyword(self, filter_obj):
        sentences = [
            "循环寿命超过2000次。",
            "本发明实施例描述如下。",
        ]
        result = filter_obj.filter(sentences)
        assert len(result) == 1
        assert "循环寿命" in result[0]

    def test_detect_english_indicator(self, filter_obj):
        sentences = [
            "The specific capacity was 170 mAh/g.",
            "The present invention relates to batteries.",
        ]
        result = filter_obj.filter(sentences)
        assert len(result) == 1
        assert "mAh/g" in result[0]

    def test_filter_rate(self, filter_obj, sample_patent_text):
        sentences = [
            s.strip()
            for s in re.split(r"[。.；;\n]", sample_patent_text)
            if s.strip()
        ]
        result = filter_obj.filter(sentences)
        assert len(result) < len(sentences)
        assert len(result) > 0
