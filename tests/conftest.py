"""Shared test fixtures."""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def sample_quintuple_dict():
    return {
        "指标名称": "能量密度",
        "指标数值": "300Wh/kg",
        "指标关系": "等于",
        "指标对象": "锂离子电池",
        "实验条件": "0.5C倍率下",
    }


@pytest.fixture
def sample_patent_text():
    return """本发明提供了一种高能量密度的锂离子电池。
    该电池的正极材料为磷酸铁锂，负极材料为石墨。
    在0.5C倍率下测试，电池的能量密度达到300Wh/kg，
    循环寿命超过2000次，库伦效率高于99.5%。
    制备过程中烧结温度为700℃，保温时间为4小时。"""


@pytest.fixture
def sample_english_patent_text():
    return """The lithium-ion battery exhibited an energy density
    of 300 Wh/kg at a discharge rate of 0.5C. The capacity
    retention after 500 cycles was 95.2%. The cathode material
    had a specific capacity of 170 mAh/g."""
