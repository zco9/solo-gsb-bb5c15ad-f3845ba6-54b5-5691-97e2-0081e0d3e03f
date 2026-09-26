"""FastAPI 入口。"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .balancer import (
    MultipleSolutionsError,
    UnbalanceableError,
    balance_reaction,
)
from .parser import FormulaSyntaxError, parse_formula
from .schemas import BalanceRequest

app = FastAPI(
    title="化学反应配平 API",
    description=(
        "输入反应物与生成物的化学式数组，基于元素守恒精确整数矩阵配平。"
        "支持元素符号、正整数下标与最多四层圆括号；不支持电荷、点号结晶水、电子。"
    ),
    version="1.0.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/balance",
    summary="配平化学反应",
    responses={
        200: {
            "description": (
                "配平结果或明确的失败原因。注意：无法配平 / 多组独立解 / "
                "非法化学式以 HTTP 400 或 200 返回，通过 balanced 与 reason 字段区分。"
            )
        }
    },
)
def balance(request: BalanceRequest) -> JSONResponse:
    # 先统一校验两侧所有化学式，一次性返回全部非法位置。
    formula_errors: list[dict] = []
    for side_name, formulas in (
        ("reactants", request.reactants),
        ("products", request.products),
    ):
        for index, formula in enumerate(formulas):
            try:
                parse_formula(formula)
            except FormulaSyntaxError as exc:
                formula_errors.append(
                    {
                        "side": side_name,
                        "index": index,
                        "formula": formula,
                        "position": exc.position,
                        "message": exc.message,
                    }
                )

    if formula_errors:
        return JSONResponse(
            status_code=400,
            content={
                "balanced": False,
                "reason": "invalid_formula",
                "message": "存在非法化学式，错误位置见 errors",
                "errors": formula_errors,
            },
        )

    try:
        result = balance_reaction(request.reactants, request.products)
    except UnbalanceableError as exc:
        return JSONResponse(
            status_code=200,
            content={
                "balanced": False,
                "reason": "unbalanceable",
                "message": str(exc),
            },
        )
    except MultipleSolutionsError as exc:
        return JSONResponse(
            status_code=200,
            content={
                "balanced": False,
                "reason": "multiple_solutions",
                "message": str(exc),
            },
        )

    return JSONResponse(status_code=200, content=result)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port)
