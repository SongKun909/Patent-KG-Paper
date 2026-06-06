"""Tests for UD to quintuple mapping."""
from syntax.mapping import UDToQuintupleMapper


class TestUDMapper:
    def test_map_nsubj_to_object(self):
        mapper = UDToQuintupleMapper()
        deps = [
            {"head": "达到", "relation": "nsubj", "child": "能量密度"},
            {"head": "能量密度", "relation": "nummod", "child": "300Wh/kg"},
        ]
        hints = mapper.map_to_hints(deps)
        assert hints["object_candidates"] == ["能量密度"]
        assert hints["value_candidates"] == ["300Wh/kg"]

    def test_map_advcl_to_condition(self):
        mapper = UDToQuintupleMapper()
        deps = [
            {"head": "测试", "relation": "advcl", "child": "0.5C倍率下"},
        ]
        hints = mapper.map_to_hints(deps)
        assert "0.5C倍率下" in hints["condition_candidates"]

    def test_map_root_to_relation(self):
        mapper = UDToQuintupleMapper()
        deps = [
            {"head": "达到", "relation": "root", "child": "达到"},
        ]
        hints = mapper.map_to_hints(deps)
        assert "达到" in hints["relation_candidates"]

    def test_empty_deps(self):
        mapper = UDToQuintupleMapper()
        hints = mapper.map_to_hints([])
        assert hints["object_candidates"] == []
        assert hints["value_candidates"] == []
