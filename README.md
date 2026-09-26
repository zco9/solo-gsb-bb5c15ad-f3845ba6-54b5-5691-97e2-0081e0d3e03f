# 化学反应配平 API

用 **Python + FastAPI + SymPy** 实现的化学反应式自动配平服务。

按元素守恒构建**精确整数矩阵**（SymPy 有理数运算，无浮点误差），仅当：

1. 矩阵零空间维数**恰为 1**，且
2. 该唯一解可以整体取号为**全部严格正整数**

时才返回配平结果；系数约成最大公约数为 1 的最小正整数，并返回反应两侧各元素的原子总数。

## 支持与不支持

**支持**

- 元素符号（1–118 号真实元素，首字母大写、最多一个小写字母）
- 正整数下标（如 `H2O`、`Fe2(SO4)3`），不允许前导 0
- **最多四层**圆括号嵌套，如 `K4(Fe(CN)6)`、`Mg2(Al(Si(BO4)2)3)2`
- 重复元素累计计数（括号内外同名元素相加）

**不支持**（直接判为非法化学式并给出字符位置）

- 电荷记号（`Na+`、`OH-` 中的 `+`/`-`）
- 电子（`e-`）
- 点号 / 中点结晶水（`CuSO4.5H2O`、`CuSO4·5H2O`）——请把 `CuSO4` 与 `5H2O` 拆成独立物质
- 方括号、花括号（请改写为圆括号）

## 一键启动（单条命令）

需要本机已安装 Docker 与 Docker Compose v2：

```bash
docker compose up --build -d
```

该命令在构建镜像时自动完成依赖安装（`pip install -r requirements.txt`），
无需任何手动安装步骤。停止服务：

```bash
docker compose down
```

### 必要配置

| 配置项 | 位置 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `BALANCER_PORT` | `docker-compose.yml` 环境变量 / `.env` | `8000` | 宿主机映射端口，如端口冲突可 `BALANCER_PORT=9000 docker compose up --build -d` |
| 容器内监听端口 | `Dockerfile` CMD | `8000` | 与 `EXPOSE` 保持一致，一般无需修改 |

### API 地址与端口

- 服务地址：`http://127.0.0.1:8000`
- 配平接口：`POST http://127.0.0.1:8000/balance`
- 健康检查：`GET http://127.0.0.1:8000/health`
- Swagger 交互文档：`http://127.0.0.1:8000/docs`
- OpenAPI Schema：`http://127.0.0.1:8000/openapi.json`

## 本地开发（不用 Docker）

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# 运行测试
pip install pytest && python -m pytest -q
```

## API 说明

### `POST /balance`

请求体：

```json
{
  "reactants": ["Fe", "O2"],
  "products": ["Fe3O4"]
}
```

- 两个数组均至少含 1 个、至多 50 个化学式；
- **数组顺序即返回系数顺序**，不做重排、不去重。

#### 成功（HTTP 200，`balanced: true`）

```json
{
  "balanced": true,
  "reactants": [
    {"formula": "Fe", "coefficient": 3},
    {"formula": "O2", "coefficient": 2}
  ],
  "products": [
    {"formula": "Fe3O4", "coefficient": 1}
  ],
  "coefficients": {"reactants": [3, 2], "products": [1]},
  "equation": "3Fe + 2O2 -> Fe3O4",
  "atom_totals": {
    "reactants": {"Fe": 3, "O": 4},
    "products": {"Fe": 3, "O": 4}
  }
}
```

`atom_totals` 给出配平后两侧**各元素的原子总数**（两侧必然相等）。

#### 无法配平（HTTP 200，`balanced: false`）

零空间为空，或唯一解含零/正负混合系数，无法得到全部严格正系数：

```json
{
  "balanced": false,
  "reason": "unbalanceable",
  "message": "元素守恒方程无解，该反应无法配平"
}
```

#### 多组独立解（HTTP 200，`balanced: false`）

零空间维数大于 1，通常因为输入混入了两个以上独立反应：

```json
{
  "balanced": false,
  "reason": "multiple_solutions",
  "message": "零空间维数为 2（大于 1），存在多组独立的配平系数"
}
```

> 「无法配平」与「存在多组独立解」通过 `reason` 字段明确区分，
> 不会返回任意一组解来冒充唯一答案。

#### 非法化学式（HTTP 400，`balanced: false`）

一次性返回两侧**全部**非法化学式，`position` 为化学式中首个非法字符的
**0 起始下标**（未闭合的 `(` 指向该括号本身）：

```json
{
  "balanced": false,
  "reason": "invalid_formula",
  "message": "存在非法化学式，错误位置见 errors",
  "errors": [
    {
      "side": "reactants",
      "index": 0,
      "formula": "CuSO4.5H2O",
      "position": 5,
      "message": "不支持点号结晶水，请将其拆成反应物/生成物中的独立物质"
    }
  ]
}
```

## 可调用示例

### curl

```bash
curl -s -X POST http://127.0.0.1:8000/balance \
  -H 'Content-Type: application/json' \
  -d '{"reactants": ["K4(Fe(CN)6)", "KMnO4", "H2SO4"],
       "products": ["KHSO4", "Fe2(SO4)3", "MnSO4", "HNO3", "CO2", "H2O"]}'
```

### Python（仅标准库）

`examples/example_call.py` 演示成功、无法配平、多组解、非法化学式四类场景：

```bash
python examples/example_call.py
# 服务地址不同时：BASE_URL=http://127.0.0.1:9000 python examples/example_call.py
```

### Python（requests）

```python
import requests

resp = requests.post(
    "http://127.0.0.1:8000/balance",
    json={"reactants": ["H2O"], "products": ["H2", "O2"]},
)
print(resp.json())
# 2H2O -> 2H2 + O2
```

## 算法与判定规则

1. 用递归下降解析器校验并解析每个化学式，得到 `{元素: 原子数}`；
2. 以物质为列、元素为行构建矩阵 `A`：反应物列取正、生成物列取负；
3. `sympy.Matrix(...).nullspace()` 在精确有理数域上求零空间：
   - 零空间维数 0 → `unbalanceable`；
   - 维数 > 1 → `multiple_solutions`；
4. 唯一基向量含零分量或正负混合 → `unbalanceable`（不存在全部严格正系数）；
5. 整体取号为正，按分母公倍数转整数，再除以全部系数的最大公约数，
   得到 gcd = 1 的最小正整数解；
6. 校验 `A·c = 0` 后返回系数与两侧原子总数。

## 项目结构

```
.
├── app/
│   ├── main.py       # FastAPI 入口（/balance、/health）
│   ├── schemas.py    # Pydantic 请求/响应模型
│   ├── balancer.py   # 元素守恒矩阵与零空间配平
│   └── parser.py     # 化学式递归下降解析（四层括号/位置报错）
├── examples/
│   └── example_call.py
├── tests/            # pytest 测试（28 个用例）
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
