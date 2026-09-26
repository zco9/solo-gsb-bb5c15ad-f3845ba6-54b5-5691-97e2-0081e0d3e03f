# 化学反应配平 API

基于 **Python + FastAPI + SymPy** 的化学反应配平服务。按元素守恒构建**精确整数矩阵**并求零空间：
仅当零空间**恰为一维**且系数可全部化为**严格正整数**时返回配平结果，系数约成最大公约数为 1 的最小正整数。

## 一键启动

```bash
docker compose up --build
```

依赖安装已纳入镜像构建（`Dockerfile` 中的 `pip install -r requirements.txt`），无需任何额外步骤。

- API 地址： **http://localhost:8000**
- 交互式文档（Swagger UI）： **http://localhost:8000/docs**
- 健康检查： `GET http://localhost:8000/health`

### 配置

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `PORT` 环境变量 | 宿主机映射端口，如 `PORT=9000 docker compose up --build` | `8000` |

## API

### `POST /balance`

请求体（JSON）：

```json
{
  "reactants": ["H2", "O2"],
  "products": ["H2O"]
}
```

#### 1. 配平成功 —— `200 OK`，`status = "balanced"`

```json
{
  "status": "balanced",
  "equation": "2 H2 + O2 -> 2 H2O",
  "coefficients": { "reactants": [2, 1], "products": [2] },
  "atom_counts": {
    "reactants": { "H": 4, "O": 2 },
    "products": { "H": 4, "O": 2 }
  }
}
```

- `coefficients`：与输入物质顺序一一对应的最小正整数系数（GCD = 1）。
- `atom_counts`：左（反应物）、右（生成物）两侧各元素的原子总数，二者必然相等。

#### 2. 无法配平 —— `200 OK`，`status = "no_solution"`

守恒方程组只有零解，或解中含异号 / 零分量（无法使全部系数严格为正）：

```json
{
  "status": "no_solution",
  "reason": "元素守恒方程组只有零解，不存在非零配平系数",
  "null_space_dimension": 0
}
```

#### 3. 存在多组独立解 —— `200 OK`，`status = "multiple_solutions"`

零空间维数大于 1，配平结果不唯一：

```json
{
  "status": "multiple_solutions",
  "reason": "零空间为 2 维，存在 2 组线性独立的配平方案，解不唯一",
  "null_space_dimension": 2
}
```

#### 4. 化学式非法 —— `400 Bad Request`，`status = "invalid_formula"`

逐个报告每个非法化学式的**所在侧、数组下标、出错字符位置（0 基）**：

```json
{
  "status": "invalid_formula",
  "errors": [
    {
      "side": "reactants",
      "index": 1,
      "formula": "H2O.5H2O",
      "position": 3,
      "message": "意外的字符 '.'"
    }
  ]
}
```

## 化学式语法

| 特性 | 支持 | 示例 |
| --- | --- | --- |
| 元素符号 | ✅ 大写字母开头 + 小写字母 | `H`、`Fe`、`Cl` |
| 正整数下标 | ✅ 省略按 1 计；`0` 非法 | `H2`、`SO4` |
| 圆括号 | ✅ 最多 **4 层**嵌套，可带倍数 | `Ca3(PO4)2`、`Mg(OH)2` |
| 重复元素 | ✅ 自动累计 | `CH3COOH` → C₂H₄O₂ |
| 电荷 | ❌ 报错并给出位置 | `SO4^2-`、`Fe3+` |
| 点号结晶水 | ❌ 报错并给出位置 | `CuSO4.5H2O` |
| 电子 | ❌ 报错并给出位置 | `e-` |

## 可调用示例

启动服务后直接运行（可用 `BASE_URL` 覆盖地址）：

```bash
bash examples.sh
```

或手动调用：

```bash
# 氢气燃烧
curl -sS -X POST http://localhost:8000/balance \
  -H 'Content-Type: application/json' \
  -d '{"reactants": ["H2", "O2"], "products": ["H2O"]}'

# 含括号：Ca3(PO4)2 + 3 H2SO4 -> 3 CaSO4 + 2 H3PO4
curl -sS -X POST http://localhost:8000/balance \
  -H 'Content-Type: application/json' \
  -d '{"reactants": ["Ca3(PO4)2", "H2SO4"], "products": ["CaSO4", "H3PO4"]}'

# 复杂反应：2 KMnO4 + 16 HCl -> 2 KCl + 2 MnCl2 + 8 H2O + 5 Cl2
curl -sS -X POST http://localhost:8000/balance \
  -H 'Content-Type: application/json' \
  -d '{"reactants": ["KMnO4", "HCl"], "products": ["KCl", "MnCl2", "H2O", "Cl2"]}'

# 无法配平：O 只出现在一侧 -> no_solution
curl -sS -X POST http://localhost:8000/balance \
  -H 'Content-Type: application/json' \
  -d '{"reactants": ["H2"], "products": ["H2O"]}'

# 多组独立解：H2/O2 可同时生成 H2O 与 H2O2 -> multiple_solutions
curl -sS -X POST http://localhost:8000/balance \
  -H 'Content-Type: application/json' \
  -d '{"reactants": ["H2", "O2"], "products": ["H2O", "H2O2"]}'

# 非法化学式：点号结晶水 -> 400，position 指出出错位置
curl -sS -X POST http://localhost:8000/balance \
  -H 'Content-Type: application/json' \
  -d '{"reactants": ["CuSO4.5H2O"], "products": ["CuSO4", "H2O"]}'
```

## 本地开发（不用 Docker）

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

运行测试：

```bash
pip install pytest httpx
pytest tests/ -v
```

## 实现说明

- `app/parser.py`：递归下降解析化学式，限制括号 4 层嵌套，重复元素累计，非法字符给出 0 基位置。
- `app/balancer.py`：以元素为行、物质为列构建精确整数矩阵（反应物取正、生成物取负），
  用 SymPy `nullspace()` 求零空间；维数为 0 → `no_solution`，大于 1 → `multiple_solutions`，
  恰为 1 时把基向量约成最小正整数，并要求全部分量严格为正。
- `app/main.py`：FastAPI 路由，`POST /balance`、`GET /health`、`GET /`。
