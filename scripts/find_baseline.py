#!/usr/bin/env python3
"""从 evo_log.jsonl 反推任务描述基线的历史对应点。"""
import json, glob, os

data_dir = os.path.expanduser('~/Agent/physcausal/data')
lines = [json.loads(l) for l in open(os.path.join(data_dir, 'evo_log.jsonl')) if l.strip()]
print("evo_log 记录数:", len(lines))
print("首条 keys:", list(lines[0].keys()))
print("末条 keys:", list(lines[-1].keys()))
print()
# 找接近基线值的时间点
for r in lines:
    r.setdefault('edges', 0)
    r.setdefault('synapse_edges', 0)
    r.setdefault('cells', 0)
    k = r.get('K', r.get('carrying_capacity', 0))
    if k:
        ratio = r['edges'] / k
        # 找 ratio ~ 177 或 0.5
        if 170 < ratio < 185 or (ratio > 0.45 and ratio < 0.55):
            print(f"gen={r['generation']} edges={r['edges']} K={k} ratio={ratio:.2f} syn={r.get('synapse_edges')} cells={r['cells']} ts={r.get('timestamp')}")

print("\n--- 各代 edges/K 序列(抽样) ---")
prev = None
for r in lines:
    k = r.get('K', 0)
    ratio = r['edges'] / k if k else 0
    mark = ''
    if prev is not None and abs(ratio - prev) > 5:
        mark = '  <-- 突变'
    if r['generation'] % 500 == 0 or mark:
        print(f"gen={r['generation']}: edges={r['edges']} K={k} ratio={ratio:.2f} syn={r.get('synapse_edges')} cells={r['cells']}{mark}")
    prev = ratio
