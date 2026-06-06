"""Tests for Integrate Agent."""
import pytest
from agents.integrate import IntegrateAgent, TERM_NORMALIZATION
from models.quintuple import Quintuple


class TestIntegrateAgent:
    @pytest.fixture
    def integrate(self):
        return IntegrateAgent()

    def test_term_normalization(self, integrate):
        assert integrate.normalize_term("库仑效率") == "库伦效率"
        assert integrate.normalize_term("coulombic efficiency") == "库伦效率"
        assert integrate.normalize_term("unknown_term") == "unknown_term"

    def test_dedup(self, integrate):
        q1 = Quintuple(
            name="能量密度", value="300Wh/kg", relation="等于",
            object="电池", condition="0.5C",
        )
        q2 = Quintuple(
            name="能量密度", value="300Wh/kg", relation="等于",
            object="电池", condition="0.5C",
        )
        result = integrate.integrate([q1, q2])
        assert len(result) == 1

    def test_keep_different_indicators(self, integrate):
        q1 = Quintuple(
            name="能量密度", value="300Wh/kg", relation="等于",
            object="电池", condition="无",
        )
        q2 = Quintuple(
            name="比容量", value="150mAh/g", relation="等于",
            object="正极", condition="无",
        )
        result = integrate.integrate([q1, q2])
        assert len(result) == 2
