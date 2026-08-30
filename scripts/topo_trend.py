#!/usr/bin/env python3
"""检查 evo_log 最近突触/边趋势 + 进程状态"""
import json, os, subprocess

DATA = os.path.expanduser('~/Agent/physcausal/data')

# evo_log 最近 30 条记录中的关键字段
rows = []
with open(os.path.join(DATA, 'evo_log.jsonl')) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass

print(f"evo_log 总条数: {len(rows)}")
if rows:
    last = rows[-1]
    print(f"最新记录 keys: {list(last.keys())}")
    print(f"最新: gen={last.get('generation')} cells={last.get('cells')} edges={last.get('edges')} syn={last.get('synapse_edges')} tier3={last.get('tier3_count')}")

# 最近 15 条带 gen 的记录
print("\n最近 15 条(gen, cells, edges, syn):")
for r in rows[-15:]:
    print(f"  gen={r.get('generation')} cells={r.get('cells')} edges={r.get('edges')} syn={r.get('synapse_edges')} t3={r.get('tier3_count')}")

# 找睡眠相关事件
sleep_events = [r for r in rows if 'sleep' in json.dumps(r).lower()]
print(f"\n睡眠相关事件条数: {len(sleep_events)}")
for r in sleep_events[-5:]:
    print(" ", json.dumps(r, ensure_ascii=False)[:200])
