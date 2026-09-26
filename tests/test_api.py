"""解析器与配平 API 的测试。"""

import pytest
from fastapi.testclient import TestClient

from app.balancer import balance_equation
from app.main import app
from app.parser import FormulaError, parse_formula

client = TestClient(app)


# ---------------- 解析器 ----------------

def test_repeated_elements_accumulate():
    assert parse_formula("CH3COOH") == {"C": 2, "H": 4, "O": 2}
    assert parse_formula("HOOH") == {"H": 2, "O": 2}
    assert parse_formula("K4Fe(CN)6") == {"K": 4, "Fe": 1, "C": 6, "N": 6}


def test_parentheses_with_multiplier():
    assert parse_formula("Ca3(PO4)2") == {"Ca": 3, "P": 2, "O": 8}
    assert parse_formula("Mg(OH)2") == {"Mg": 1, "O": 2, "H": 2}


def test_four_nesting_levels_allowed():
    # 四层圆括号：( ( ( ( CH3 )2 )2 )2 ) -> C8H24
    assert parse_formula("((((CH3)2)2)2)") == {"C": 8, "H": 24}


def test_five_nesting_levels_rejected_with_position():
    with pytest.raises(FormulaError) as exc:
        parse_formula("(((((A)))))")
    assert exc.value.position == 4  # 第 5 个左括号的位置


def test_invalid_characters_report_position():
    with pytest.raises(FormulaError) as exc:
        parse_formula("h2o")  # 小写字母开头
    assert exc.value.position == 0

    with pytest.raises(FormulaError) as exc:
        parse_formula("H2O.")  # 不支持点号结晶水
    assert exc.value.position == 3

    with pytest.raises(FormulaError) as exc:
        parse_formula("SO4^2-")  # 不支持电荷
    assert exc.value.position == 3

    with pytest.raises(FormulaError) as exc:
        parse_formula("H2e-")  # 不支持电子 / 连字符
    assert exc.value.position == 2


def test_zero_subscript_rejected():
    with pytest.raises(FormulaError) as exc:
        parse_formula("H0")
    assert exc.value.position == 1

    with pytest.raises(FormulaError) as exc:
        parse_formula("(H2O)0")
    assert exc.value.position == 5


def test_empty_and_unclosed_parentheses():
    with pytest.raises(FormulaError) as exc:
        parse_formula("Ca()2")
    assert exc.value.position == 3

    with pytest.raises(FormulaError) as exc:
        parse_formula("Ca(OH")
    assert exc.value.position == 5  # 字符串末尾


def test_empty_formula_rejected():
    with pytest.raises(FormulaError) as exc:
        parse_formula("")
    assert exc.value.position == 0


# ---------------- 配平核心 ----------------

def test_water_electrolysis():
    result = balance_equation(["H2", "O2"], ["H2O"])
    assert result.status == "balanced"
    assert result.coefficients == {"reactants": [2, 1], "products": [2]}
    assert result.atom_counts == {
        "reactants": {"H": 4, "O": 2},
        "products": {"H": 4, "O": 2},
    }
    assert result.equation == "2 H2 + O2 -> 2 H2O"


def test_phosphoric_acid_with_parentheses():
    result = balance_equation(
        ["Ca3(PO4)2", "H2SO4"], ["CaSO4", "H3PO4"]
    )
    assert result.coefficients == {"reactants": [1, 3], "products": [3, 2]}
    assert result.atom_counts["reactants"] == {"Ca": 3, "P": 2, "O": 20, "H": 6, "S": 3}
    assert result.atom_counts["products"] == {"Ca": 3, "P": 2, "O": 20, "H": 6, "S": 3}


def test_pyrite_roasting():
    result = balance_equation(["FeS2", "O2"], ["Fe2O3", "SO2"])
    assert result.coefficients == {"reactants": [4, 11], "products": [2, 8]}


def test_kmno4_hcl():
    result = balance_equation(
        ["KMnO4", "HCl"], ["KCl", "MnCl2", "H2O", "Cl2"]
    )
    assert result.coefficients == {"reactants": [2, 16], "products": [2, 2, 8, 5]}


def test_gcd_reduced_and_order_preserved():
    result = balance_equation(["H2", "O2"], ["H2O"])
    coeffs = result.coefficients["reactants"] + result.coefficients["products"]
    from math import gcd
    from functools import reduce
    assert reduce(gcd, coeffs) == 1


def test_no_solution_missing_element():
    result = balance_equation(["H2"], ["H2O"])
    assert result.status == "no_solution"
    assert result.null_space_dimension == 0


def test_no_solution_zero_coefficient_required():
    # 2 H2O + CO2 -> H2CO3 + ?O2 只能让 O2 系数为 0
    result = balance_equation(["H2O", "CO2"], ["H2CO3", "O2"])
    assert result.status == "no_solution"


def test_multiple_solutions_distinguished():
    result = balance_equation(["H2", "O2"], ["H2O", "H2O2"])
    assert result.status == "multiple_solutions"
    assert result.null_space_dimension == 2


# ---------------- HTTP API ----------------

def test_api_balanced():
    resp = client.post("/balance", json={"reactants": ["H2", "O2"], "products": ["H2O"]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "balanced"
    assert data["coefficients"] == {"reactants": [2, 1], "products": [2]}


def test_api_invalid_formula_400_with_position():
    resp = client.post(
        "/balance", json={"reactants": ["H2", "2O", "O2"], "products": ["H2O"]}
    )
    assert resp.status_code == 400
    errors = resp.json()["errors"]
    assert len(errors) == 1
    err = errors[0]
    assert err["side"] == "reactants"
    assert err["index"] == 1
    assert err["position"] == 0


def test_api_nested_parens_error():
    resp = client.post(
        "/balance",
        json={"reactants": ["H2"], "products": ["H(((((O))))))"]},
    )
    assert resp.status_code == 400
    assert resp.json()["errors"][0]["position"] == 5  # 第 5 个左括号超出 4 层限制


def test_api_no_solution_and_multiple():
    resp = client.post("/balance", json={"reactants": ["H2"], "products": ["H2O"]})
    assert resp.json()["status"] == "no_solution"

    resp = client.post(
        "/balance", json={"reactants": ["H2", "O2"], "products": ["H2O", "H2O2"]}
    )
    body = resp.json()
    assert body["status"] == "multiple_solutions"
    assert body["null_space_dimension"] == 2


def test_api_empty_lists_rejected():
    resp = client.post("/balance", json={"reactants": [], "products": ["H2O"]})
    assert resp.status_code == 422


def test_health_and_index():
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/").json()["service"] == "chemical-equation-balancer"
