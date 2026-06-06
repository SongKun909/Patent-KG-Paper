"""Tests for F1* metric."""
from eval.f1_star import compute_f1_star, _element_similarity


class TestElementSimilarity:
    def test_exact_match(self):
        assert _element_similarity("300Wh/kg", "300Wh/kg") == 1.0

    def test_substring_match(self):
        assert _element_similarity("300Wh/kg", "300 Wh/kg") > 0.5

    def test_no_match(self):
        assert _element_similarity("能量密度", "比容量") == 0.0


class TestF1Star:
    def test_perfect_extraction(self):
        pred = [{"指标名称":"能量密度","指标数值":"300Wh/kg",
                  "指标关系":"等于","指标对象":"电池","实验条件":"0.5C"}]
        gold = [{"指标名称":"能量密度","指标数值":"300Wh/kg",
                  "指标关系":"等于","指标对象":"电池","实验条件":"0.5C"}]
        result = compute_f1_star(pred, gold)
        assert result.f1_star > 0.9

    def test_empty_gold(self):
        result = compute_f1_star([], [])
        assert result.f1_star == 0.0

    def test_no_gold_no_pred(self):
        result = compute_f1_star(
            [{"指标名称":"x"}],
            [{"指标名称":"y"}],
        )
        assert result.f1_star == 0.0  # Core mismatch → one-vote veto

    def test_element_scores(self):
        pred = [{"指标名称":"能量密度","指标数值":"300Wh/kg",
                  "指标关系":"等于","指标对象":"电池","实验条件":"0.5C"}]
        gold = [{"指标名称":"能量密度","指标数值":"300Wh/kg",
                  "指标关系":"等于","指标对象":"电池","实验条件":"0.5C"}]
        result = compute_f1_star(pred, gold)
        assert "name" in result.element_scores
        assert result.element_scores["name"] > 0.9
        assert result.completeness == 1.0
