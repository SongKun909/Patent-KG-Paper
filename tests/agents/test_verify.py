"""Tests for Verify Agent."""
import pytest
from agents.verify import VerifyAgent
from models.quintuple import Quintuple


class TestVerifyAgent:
    @pytest.fixture
    def verify(self):
        return VerifyAgent()

    def test_pass_valid_quintuple(self, verify):
        q = Quintuple(
            name="能量密度", value="300Wh/kg", relation="等于",
            object="电池", condition="0.5C",
        )
        results = verify.verify([q])
        assert results[0]["verdict"] == "pass"

    def test_fail_missing_elements(self, verify):
        q = Quintuple(name="", value="", relation="", object="", condition="")
        results = verify.verify([q])
        assert results[0]["verdict"] == "fail"
        assert results[0]["severity"] == "critical"

    def test_fail_out_of_bounds(self, verify):
        q = Quintuple(
            name="能量密度", value="999999Wh/kg", relation="等于",
            object="电池", condition="无",
        )
        results = verify.verify([q])
        assert results[0]["verdict"] == "fail"

    def test_multiple_quintuples(self, verify):
        good = Quintuple(
            name="比容量", value="150mAh/g", relation="等于",
            object="正极", condition="0.5C",
        )
        bad = Quintuple(name="", value="", relation="", object="", condition="")
        results = verify.verify([good, bad])
        assert results[0]["verdict"] == "pass"
        assert results[1]["verdict"] == "fail"
