#!/usr/bin/env python3
"""确认 vs.cache / emergent_edges 边结构 + 历史快照序列分析。"""
import json, gzip, glob, os

data_dir = os.path.expanduser('~/Agent/physcausal/data')

def load(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)

# 1) 边结构样本
kg = load(data_dir + '/evo_snapshot_gen38455_kg.json')
vc = kg['vs.cache']
print("=== vs.cache 边样本 ===")
cnt = 0
for node, rec in vc.items():
    if not isinstance(rec, dict): continue
    for key in ('effects', 'causes'):
        for e in rec.get(key, []) or []:
            print(f"{node} {key}: {json.dumps(e, ensure_ascii=False)[:200]}")
            cnt += 1
            if cnt >= 10: break
    if cnt >= 10: break

from collections import Counter
print("\n=== vs.cache e[2] 值分布 (top 12) ===")
kinds = Counter()
for node, rec in vc.items():
    if not isinstance(rec, dict): continue
    for key in ('effects', 'causes'):
        for e in rec.get(key, []) or []:
            if isinstance(e, (list, tuple)) and len(e) >= 3:
                kinds[str(e[2])] += 1
for k, v in kinds.most_common(12):
    print(f"  {k}: {v}")
print("总边:", sum(kinds.values()))

print("\n=== emergent_edges 样本 ===")
ee = kg.get('emergent_edges', [])
for e in ee[:5]:
    print(json.dumps(e, ensure_ascii=False)[:250])
