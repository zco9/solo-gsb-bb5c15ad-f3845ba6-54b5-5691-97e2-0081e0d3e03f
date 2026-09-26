import pytest

from app.balancer import (
    MultipleSolutionsError,
    UnbalanceableError,
    balance_reaction,
)


def test_simple_balance():
    result = balance_reaction(["Fe", "O2"], ["Fe3O4"])
    assert result["coefficients"] == {"reactants": [3, 2], "products": [1]}
    assert result["equation"] == "3Fe + 2O2 -> Fe3O4"
    assert result["atom_totals"]["reactants"] == {"Fe": 3, "O": 4}
    assert result["atom_totals"]["products"] == {"Fe": 3, "O": 4}


def test_order_is_preserved():
    result = balance_reaction(["O2", "Fe"], ["Fe3O4"])
    assert result["coefficients"] == {"reactants": [2, 3], "products": [1]}
    assert result["reactants"][0]["formula"] == "O2"
    assert result["reactants"][1]["formula"] == "Fe"


def test_water_electrolysis():
    result = balance_reaction(["H2O"], ["H2", "O2"])
    assert result["coefficients"] == {"reactants": [2], "products": [2, 1]}
    totals = result["atom_totals"]
    assert totals["reactants"] == totals["products"] == {"H": 4, "O": 2}


def test_coefficients_are_minimal_gcd_one():
    # KMnO4 + HCl -> KCl + MnCl2 + Cl2 + H2O 的经典配平
    result = balance_reaction(
        ["KMnO4", "HCl"],
        ["KCl", "MnCl2", "Cl2", "H2O"],
    )
    coeffs = (
        result["coefficients"]["reactants"]
        + result["coefficients"]["products"]
    )
    assert coeffs == [2, 16, 2, 2, 5, 8]
    from math import gcd
    from functools import reduce

    assert reduce(gcd, coeffs) == 1


def test_nested_parentheses_balance():
    # 黄血盐 + 高锰酸钾酸性体系（示例中使用的反应）
    result = balance_reaction(
        ["K4(Fe(CN)6)", "KMnO4", "H2SO4"],
        ["KHSO4", "Fe2(SO4)3", "MnSO4", "HNO3", "CO2", "H2O"],
    )
    left = result["atom_totals"]["reactants"]
    right = result["atom_totals"]["products"]
    assert left == right
    assert all(c > 0 for c in result["coefficients"]["reactants"])
    assert all(c > 0 for c in result["coefficients"]["products"])
    assert result["coefficients"]["reactants"][0] == 10
    assert result["coefficients"]["reactants"][1] == 122


def test_unbalanceable_full_rank_no_solution():
    # 产物多了一个反应物中不存在的元素，且约束满秩：零空间为空
    with pytest.raises(UnbalanceableError):
        balance_reaction(["H2", "O2"], ["HFeO2"])


def test_unbalanceable_zero_coefficient_distinguished():
    # H2 + O2 -> H2O + Fe：Fe 列被迫为 0，唯一解含零系数
    with pytest.raises(UnbalanceableError):
        balance_reaction(["H2", "O2"], ["H2O", "Fe"])


def test_multiple_solutions():
    # C + O2 + CO -> CO2：CO + 1/2 O2 -> CO2 与 C + O2 -> CO2 两个独立反应
    with pytest.raises(MultipleSolutionsError):
        balance_reaction(["C", "O2", "CO"], ["CO2"])


def test_zero_coefficient_solution_is_unbalanceable():
    # 体系中混入一个与反应无关的物质时，唯一解里它的系数可能是 0
    with pytest.raises(UnbalanceableError):
        balance_reaction(["H2", "O2", "N2"], ["H2O"])


def test_single_species_reaction():
    # 同素异形体：O3 -> O2
    result = balance_reaction(["O3"], ["O2"])
    assert result["coefficients"] == {"reactants": [2], "products": [3]}


def test_repeated_formula_entries():
    # 同一物质出现两次：H2 + H2 -> H2O ... 无法配平（O 无来源）
    with pytest.raises(UnbalanceableError):
        balance_reaction(["H2", "H2"], ["H2O"])
