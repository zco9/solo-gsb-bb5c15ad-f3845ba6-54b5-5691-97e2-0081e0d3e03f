"""化学反应配平 API（FastAPI + SymPy）。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .balancer import (
    STATUS_INVALID,
    balance_equation,
)
from .schemas import (
    BalancedResponse,
    BalanceRequest,
    InvalidFormulaResponse,
    UnbalancedResponse,
)

app = FastAPI(
    title="化学反应配平 API",
    version="1.0.0",
    description=(
        "按元素守恒构建精确整数矩阵并求零空间，仅当零空间恰为一维且系数可全部化为"
        "严格正整数时返回配平结果。化学式支持元素符号、正整数下标、最多四层圆括号；"
        "不支持电荷、点号结晶水和电子。"
    ),
)


@app.get("/", summary="服务信息")
def index():
    return {
        "service": "chemical-equation-balancer",
        "docs": "/docs",
        "balance": "POST /balance",
        "health": "GET /health",
    }


@app.get("/health", summary="健康检查")
def health():
    return {"status": "ok"}


@app.post(
    "/balance",
    response_model=BalancedResponse | UnbalancedResponse,
    responses={400: {"model": InvalidFormulaResponse, "description": "化学式非法"}},
    summary="配平化学反应",
)
def balance(request: BalanceRequest):
    result = balance_equation(request.reactants, request.products)

    if result.status == STATUS_INVALID:
        return JSONResponse(
            status_code=400,
            content={
                "status": STATUS_INVALID,
                "errors": [vars(e) for e in result.invalid_formulas],
            },
        )

    if result.status == "balanced":
        return BalancedResponse(
            equation=result.equation,
            coefficients=result.coefficients,
            atom_counts=result.atom_counts,
        )

    return UnbalancedResponse(
        status=result.status,
        reason=result.reason,
        null_space_dimension=result.null_space_dimension,
    )
