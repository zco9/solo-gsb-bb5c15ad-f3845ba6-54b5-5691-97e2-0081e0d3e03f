"""化学式解析器。

支持的语法：
  - 元素符号：一个大写 ASCII 字母后跟零个或多个小写 ASCII 字母（如 H、Fe、Cl）
  - 正整数下标（如 H2、SO4），省略时按 1 计
  - 圆括号分组，最多嵌套 MAX_DEPTH 层，括号后可跟正整数倍数（如 Ca3(PO4)2）
  - 同一元素多次出现时累计计数（如 CH3COOH -> C2H4O2）

不支持（解析时报错并给出位置）：电荷（+、-、^）、结晶水点号（.、·）、电子（e-）。
"""

from __future__ import annotations

MAX_DEPTH = 4


class FormulaError(Exception):
    """化学式非法。position 为出错字符在化学式中的位置（0 基索引）。"""

    def __init__(self, message: str, position: int):
        super().__init__(f"{message} (position {position})")
        self.message = message
        self.position = position


def parse_formula(formula: str) -> dict[str, int]:
    """把化学式解析为 {元素符号: 原子数}。"""
    if not isinstance(formula, str) or formula == "":
        raise FormulaError("化学式不能为空", 0)
    counts, pos = _parse_sequence(formula, 0, depth=0)
    if pos < len(formula):
        raise FormulaError(f"意外的字符 {formula[pos]!r}", pos)
    return counts


def _parse_sequence(s: str, pos: int, depth: int) -> tuple[dict[str, int], int]:
    """解析若干「元素/括号组 + 可选下标」，直到字符串末尾或右括号。"""
    counts: dict[str, int] = {}
    n = len(s)
    start = pos
    while pos < n and s[pos] != ")":
        ch = s[pos]
        if ch == "(":
            if depth >= MAX_DEPTH:
                raise FormulaError(f"圆括号嵌套超过 {MAX_DEPTH} 层", pos)
            inner, pos = _parse_sequence(s, pos + 1, depth + 1)
            if pos >= n:  # 内层在字符串末尾结束，说明没有匹配的右括号
                raise FormulaError("缺少右括号 ')'", pos)
            pos += 1  # 跳过 ')'
            multiplier, pos = _parse_number(s, pos)
            for element, count in inner.items():
                counts[element] = counts.get(element, 0) + count * multiplier
        elif _is_upper(ch):
            element, pos = _parse_element(s, pos)
            number, pos = _parse_number(s, pos)
            counts[element] = counts.get(element, 0) + number
        else:
            raise FormulaError(f"意外的字符 {ch!r}", pos)
    if depth > 0 and pos == start:
        raise FormulaError("括号内不能为空", pos)
    return counts, pos


def _parse_element(s: str, pos: int) -> tuple[str, int]:
    start = pos
    pos += 1  # 大写字母
    while pos < len(s) and _is_lower(s[pos]):
        pos += 1
    return s[start:pos], pos


def _parse_number(s: str, pos: int) -> tuple[int, int]:
    """解析可选的正整数下标，省略时返回 1。"""
    if pos >= len(s) or not _is_digit(s[pos]):
        return 1, pos
    if s[pos] == "0":
        raise FormulaError("下标必须为正整数", pos)
    start = pos
    while pos < len(s) and _is_digit(s[pos]):
        pos += 1
    return int(s[start:pos]), pos


def _is_upper(ch: str) -> bool:
    return "A" <= ch <= "Z"


def _is_lower(ch: str) -> bool:
    return "a" <= ch <= "z"


def _is_digit(ch: str) -> bool:
    return "0" <= ch <= "9"
