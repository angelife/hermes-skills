#!/usr/bin/env bash
# verify_hindsight.sh — 端到端验证 hindsight 读写连通性
# 用法: bash verify_hindsight.sh
# 必须已设置 HINDSIGHT_API_URL 和 HINDSIGHT_API_KEY

set -euo pipefail

cd "$(dirname "$0")/.."
HERMES_VENV="${HERMES_HOME:-$HOME/.hermes}/hermes-agent/venv"
PY="$HERMES_VENV/bin/python3"

if [ ! -f "$PY" ]; then
  echo "❌ 找不到 Hermes venv 的 Python: $PY"
  exit 1
fi

"$PY" << 'PYEOF'
import os, sys, json

env_path = os.path.expanduser("~/.hermes/.env")
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if "=" not in line or line.startswith("#"):
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)

api_url = os.environ.get("HINDSIGHT_API_URL", "")
api_key = os.environ.get("HINDSIGHT_API_KEY", "")
bank_id = os.environ.get("HINDSIGHT_BANK_ID", "hermes")

if not api_url:
    print("❌ HINDSIGHT_API_URL 未设置")
    sys.exit(1)
if not api_key:
    print("❌ HINDSIGHT_API_KEY 未设置")
    sys.exit(1)

import pathlib
cfg_path = pathlib.Path.home() / ".hermes" / "hindsight" / "config.json"
if cfg_path.exists():
    cfg = json.loads(cfg_path.read_text())
    mode = cfg.get("mode", "unknown")
else:
    mode = "unknown (no config.json)"

print(f"  URL: {api_url}")
print(f"  KEY: {api_key[:12]}...{api_key[-4:]}")
print(f"  BANK: {bank_id}")
print(f"  MODE: {mode}")

from hindsight_client import Hindsight
h = Hindsight(api_key=api_key, base_url=api_url)

import uuid, time
marker = f"连通性验证_{uuid.uuid4().hex[:8]}"
print(f"\n🟢 写入: {marker}")
ret = h.retain(bank_id=bank_id, content=marker, context="hindsight连通性测试")
assert ret.success, f"Retain failed: {ret}"
print(f"   ✅ retain 成功 (items={ret.items_count})")

time.sleep(1)
print(f"\n🟢 召回: {marker[:12]}...")
rec = h.recall(bank_id=bank_id, query=marker, budget="low")
found = False
for r in (rec.results or []):
    if marker in r.text:
        print(f"   ✅ 找到: {r.text}")
        found = True
        break
if not found:
    print("   ❌ 未找到标记 — 服务可能不通")
    for r in (rec.results or [])[:3]:
        print(f"   结果: {r.text[:60]}")
    sys.exit(1)

total = len(rec.results or [])
print(f"\n✅ 验证通过 (查询返回 {total} 条结果)")
PYEOF
