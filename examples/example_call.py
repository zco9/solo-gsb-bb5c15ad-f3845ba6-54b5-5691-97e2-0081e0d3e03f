"""配平 API 调用示例（仅依赖 Python 标准库）。

用法::

    # 先启动服务
    docker compose up --build -d

    # 再运行示例（默认 http://127.0.0.1:8000，可用环境变量 BASE_URL 覆盖）
    python examples/example_call.py
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")


def call_balance(reactants: list[str], products: list[str]) -> dict:
    payload = json.dumps(
        {"reactants": reactants, "products": products}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}/balance",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 非法化学式返回 400，响应体仍是同样的 JSON 结构
        return json.loads(exc.read().decode("utf-8"))


def show(title: str, reactants: list[str], products: list[str]) -> None:
    print(f"=== {title} ===")
    print(f"请求: reactants={reactants}, products={products}")
    result = call_balance(reactants, products)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()


def main() -> None:
    # 1. 普通配平：Fe + O2 -> Fe3O4  =>  3Fe + 2O2 -> Fe3O4
    show("普通配平", ["Fe", "O2"], ["Fe3O4"])

    # 2. 四层括号 + 重复元素累计：K4(Fe(CN)6) 参与的反应
    show(
        "复杂括号",
        ["K4(Fe(CN)6)", "KMnO4", "H2SO4"],
        ["KHSO4", "Fe2(SO4)3", "MnSO4", "HNO3", "CO2", "H2O"],
    )

    # 3. 无法配平：H2 + O2 -> H2O + Fe
    show("无法配平", ["H2", "O2"], ["H2O", "Fe"])

    # 4. 多组独立解：C + O2 + CO -> CO2
    show("多组独立解", ["C", "O2", "CO"], ["CO2"])

    # 5. 非法化学式（电荷、点号结晶水不支持；下标位置非法）
    show("非法化学式", ["CuSO4.5H2O"], ["CuSO4", "H2O"])
    show("非法字符位置", ["H2O", "Na+"], ["NaOH"])


if __name__ == "__main__":
    main()
