#!/usr/bin/env bash
# 可调用示例：默认访问 http://localhost:8000，可用 BASE_URL 环境变量覆盖。
set -u
BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "== 1. 氢气燃烧：2 H2 + O2 -> 2 H2O =="
curl -sS -X POST "$BASE_URL/balance" \
  -H 'Content-Type: application/json' \
  -d '{"reactants": ["H2", "O2"], "products": ["H2O"]}'
echo

echo "== 2. 含括号：Ca3(PO4)2 + 3 H2SO4 -> 3 CaSO4 + 2 H3PO4 =="
curl -sS -X POST "$BASE_URL/balance" \
  -H 'Content-Type: application/json' \
  -d '{"reactants": ["Ca3(PO4)2", "H2SO4"], "products": ["CaSO4", "H3PO4"]}'
echo

echo "== 3. 重复元素累计 + 复杂反应：2 KMnO4 + 16 HCl -> ... =="
curl -sS -X POST "$BASE_URL/balance" \
  -H 'Content-Type: application/json' \
  -d '{"reactants": ["KMnO4", "HCl"], "products": ["KCl", "MnCl2", "H2O", "Cl2"]}'
echo

echo "== 4. 无法配平（O 只出现在一侧）= "
curl -sS -X POST "$BASE_URL/balance" \
  -H 'Content-Type: application/json' \
  -d '{"reactants": ["H2"], "products": ["H2O"]}'
echo

echo "== 5. 存在多组独立解（零空间二维）= "
curl -sS -X POST "$BASE_URL/balance" \
  -H 'Content-Type: application/json' \
  -d '{"reactants": ["H2", "O2"], "products": ["H2O", "H2O2"]}'
echo

echo "== 6. 非法化学式：下标位置非法，返回 400 与出错位置 = "
curl -sS -X POST "$BASE_URL/balance" \
  -H 'Content-Type: application/json' \
  -d '{"reactants": ["H2", "H2O.5H2O"], "products": ["H2O"]}'
echo
