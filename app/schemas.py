"""请求 / 响应模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BalanceRequest(BaseModel):
    reactants: list[str] = Field(..., min_length=1, description="反应物化学式数组")
    products: list[str] = Field(..., min_length=1, description="生成物化学式数组")

    model_config = {
        "json_schema_extra": {
            "examples": [{"reactants": ["H2", "O2"], "products": ["H2O"]}]
        }
    }


class Coefficients(BaseModel):
    reactants: list[int] = Field(..., description="反应物系数，顺序与输入一致")
    products: list[int] = Field(..., description="生成物系数，顺序与输入一致")


class AtomCounts(BaseModel):
    reactants: dict[str, int] = Field(..., description="左侧各元素原子总数")
    products: dict[str, int] = Field(..., description="右侧各元素原子总数")


class BalancedResponse(BaseModel):
    status: Literal["balanced"] = "balanced"
    equation: str
    coefficients: Coefficients
    atom_counts: AtomCounts


class UnbalancedResponse(BaseModel):
    status: Literal["no_solution", "multiple_solutions"]
    reason: str
    null_space_dimension: int = Field(..., description="守恒矩阵零空间的维数")


class InvalidFormulaItem(BaseModel):
    side: Literal["reactants", "products"]
    index: int = Field(..., description="化学式在对应数组中的下标")
    formula: str
    position: int = Field(..., description="出错字符位置（0 基索引）")
    message: str


class InvalidFormulaResponse(BaseModel):
    status: Literal["invalid_formula"] = "invalid_formula"
    errors: list[InvalidFormulaItem]
