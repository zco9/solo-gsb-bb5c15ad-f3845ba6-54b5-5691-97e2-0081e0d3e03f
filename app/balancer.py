"""配平核心：按元素守恒构建精确整数矩阵，用 SymPy 求零空间。

设物质 j 中元素 i 的原子数为 a_ij，反应物取正、生成物取负构成矩阵 A，
则配平系数向量 x 满足 A·x = 0。仅当零空间恰为一维且基向量可化为
全部严格正的整数时，配平结果唯一（约成最大公约数为 1 的最小正整数）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import gcd

import sympy as sp

from .parser import FormulaError, parse_formula

STATUS_BALANCED = "balanced"
STATUS_NO_SOLUTION = "no_solution"
STATUS_MULTIPLE = "multiple_solutions"
STATUS_INVALID = "invalid_formula"


@dataclass
class InvalidFormula:
    side: str       # "reactants" | "products"
    index: int      # 化学式在对应数组中的下标
    formula: str
    position: int   # 出错字符位置（0 基索引）
    message: str


@dataclass
class BalanceResult:
    status: str
    coefficients: dict | None = None    # {"reactants": [...], "products": [...]}
    atom_counts: dict | None = None     # {"reactants": {...}, "products": {...}}
    equation: str | None = None
    reason: str | None = None
    null_space_dimension: int = 0
    invalid_formulas: list[InvalidFormula] = field(default_factory=list)


def balance_equation(reactants: list[str], products: list[str]) -> BalanceResult:
    # 1. 解析全部化学式，收集所有非法化学式及其出错位置
    parsed_r = _parse_side(reactants, "reactants")
    parsed_p = _parse_side(products, "products")
    errors = [e for _, e in parsed_r if e is not None] + \
             [e for _, e in parsed_p if e is not None]
    if errors:
        return BalanceResult(status=STATUS_INVALID, invalid_formulas=errors)
    counts_r = [c for c, _ in parsed_r]
    counts_p = [c for c, _ in parsed_p]

    # 2. 元素按首次出现顺序排列，构建精确整数矩阵（反应物为正，生成物为负）
    species = counts_r + counts_p
    elements: list[str] = []
    for counts in species:
        for element in counts:
            if element not in elements:
                elements.append(element)
    matrix = sp.Matrix([
        [c.get(el, 0) for c in counts_r] + [-c.get(el, 0) for c in counts_p]
        for el in elements
    ])

    # 3. 求零空间，仅当恰为一维时才可能有唯一解
    null_space = matrix.nullspace()
    dim = len(null_space)
    if dim == 0:
        return BalanceResult(
            status=STATUS_NO_SOLUTION,
            reason="元素守恒方程组只有零解，不存在非零配平系数",
            null_space_dimension=0,
        )
    if dim > 1:
        return BalanceResult(
            status=STATUS_MULTIPLE,
            reason=f"零空间为 {dim} 维，存在 {dim} 组线性独立的配平方案，解不唯一",
            null_space_dimension=dim,
        )

    # 4. 约成最小正整数，要求全部系数严格为正
    coeffs = _to_minimal_integers(null_space[0])
    if all(c < 0 for c in coeffs):
        coeffs = [-c for c in coeffs]
    if not all(c > 0 for c in coeffs):
        return BalanceResult(
            status=STATUS_NO_SOLUTION,
            reason="守恒方程的解含异号或零分量，无法使全部系数严格为正",
            null_space_dimension=1,
        )

    # 5. 汇总结果：系数（保持输入顺序）、两侧各元素原子总数、方程式
    n_r = len(counts_r)
    coeff_r, coeff_p = coeffs[:n_r], coeffs[n_r:]
    atom_counts = {
        side: {
            el: sum(c * counts.get(el, 0) for c, counts in zip(coeffs_side, counts_side))
            for el in elements
        }
        for side, coeffs_side, counts_side in (
            ("reactants", coeff_r, counts_r),
            ("products", coeff_p, counts_p),
        )
    }
    return BalanceResult(
        status=STATUS_BALANCED,
        coefficients={"reactants": coeff_r, "products": coeff_p},
        atom_counts=atom_counts,
        equation=f"{_format_side(coeff_r, reactants)} -> {_format_side(coeff_p, products)}",
        null_space_dimension=1,
    )


def _parse_side(formulas: list[str], side: str):
    """解析一侧的化学式，返回 [(counts|None, InvalidFormula|None)]。"""
    parsed = []
    for index, formula in enumerate(formulas):
        try:
            parsed.append((parse_formula(formula), None))
        except FormulaError as e:
            parsed.append((None, InvalidFormula(side, index, formula, e.position, e.message)))
    return parsed


def _to_minimal_integers(vector) -> list[int]:
    """把精确有理数向量约成最大公约数为 1 的最小整数向量。"""
    lcm = 1
    for v in vector:
        lcm = sp.ilcm(lcm, sp.denom(v))
    ints = [int(v * lcm) for v in vector]
    common = 0
    for v in ints:
        common = gcd(common, abs(v))
    if common > 1:
        ints = [v // common for v in ints]
    return ints


def _format_side(coeffs: list[int], formulas: list[str]) -> str:
    return " + ".join(f if c == 1 else f"{c} {f}" for c, f in zip(coeffs, formulas))
