import pytest

from app.parser import FormulaSyntaxError, parse_formula


def test_simple_formulas():
    assert parse_formula("H2O") == {"H": 2, "O": 1}
    assert parse_formula("H2") == {"H": 2}
    assert parse_formula("He") == {"He": 1}
    assert parse_formula("Fe3O4") == {"Fe": 3, "O": 4}


def test_repeated_elements_accumulate():
    # COOH 中 O 出现两次
    assert parse_formula("COOH") == {"C": 1, "O": 2, "H": 1}
    # 括号内外同名元素累加
    assert parse_formula("Mg2(OH)2") == {"Mg": 2, "O": 2, "H": 2}
    assert parse_formula("Ca3(PO4)2") == {"Ca": 3, "P": 2, "O": 8}
    assert parse_formula("K4(Fe(CN)6)") == {"K": 4, "Fe": 1, "C": 6, "N": 6}


def test_nested_parentheses_up_to_four_levels():
    # 四层：a(b(c(d)e)f)g 形式
    assert parse_formula("Mg2(Al(Si(BO4)2)3)2") == {
        "Mg": 2,
        "Al": 2,
        "Si": 6,
        "B": 12,
        "O": 48,
    }


def test_five_levels_rejected():
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("(((((H)))))")
    assert exc.value.position == 4  # 第五个 '(' 的位置
    assert "4 层" in exc.value.message


def test_unknown_element():
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("X2O")
    assert exc.value.position == 0

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("Nx")
    assert exc.value.position == 0  # 'Nx' 不是任何元素

    # 按“最多一个小写字母”的文法，Nacl 在 c 处即判为大小写错误
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("Nacl")
    assert exc.value.position == 2


def test_invalid_subscript():
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("H0")
    assert exc.value.position == 1

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("H01")
    assert exc.value.position == 1

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("(H2)0")
    assert exc.value.position == 4


def test_unclosed_and_extra_parenthesis():
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("Ca(OH2")
    assert exc.value.position == 2
    assert "未闭合" in exc.value.message

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("H2O)")
    assert exc.value.position == 3
    assert "配对" in exc.value.message

    with pytest.raises(FormulaSyntaxError):
        parse_formula("()2")


def test_unsupported_features_are_rejected_with_position():
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("CuSO4.5H2O")
    assert exc.value.position == 5

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("CuSO4·5H2O")
    assert exc.value.position == 5

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("Na+")
    assert exc.value.position == 2

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("e-")
    assert exc.value.position == 0  # 'e' 为小写，先报大小写错误

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("[Cu(NH3)4]SO4")
    assert exc.value.position == 0

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("H2 O")
    assert exc.value.position == 2


def test_empty_and_leading_digit():
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("")
    assert exc.value.position == 0

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("2H")
    assert exc.value.position == 0

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("H2 3")
    assert exc.value.position == 2
