#!/usr/bin/env python3
"""精确统计 vs.cache emergent 边 composed/hebbian label（effects用e[0], causes用e[1]）+ emergent_edges.json。"""
import json, gzip

def load(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)

kg = load('/home/duyw/Agent/physcausal/data/evo_snapshot_gen39455_kg.json')
vc = kg['vs.cache']

from collections import Counter
lab_em = Counter()   # emergent 边的 label 分布
composed = hebbian = other = 0
other_labels = Counter()
for node, rec in vc.items():
    if not isinstance(rec, dict): continue
    # effects: [label, target, kind]
    for e in rec.get('effects', []) or []:
        if isinstance(e, (list, tuple)) and len(e) >= 3 and e[2] == 'emergent':
            label = str(e[0]).lower()
            lab_em[label] += 1
            if 'composed' in label: composed += 1
            elif 'hebbian' in label: hebbian += 1
            else:
                other += 1
                other_labels[label] += 1
    # causes: [source, label, kind]
    for e in rec.get('causes', []) or []:
        if isinstance(e, (list, tuple)) and len(e) >= 3 and e[2] == 'emergent':
            label = str(e[1]).lower()
            lab_em[label] += 1
            if 'composed' in label: composed += 1
            elif 'hebbian' in label: hebbian += 1
            else:
                other += 1
                other_labels[label] += 1

total = sum(lab_em.values())
print(f"vs.cache emergent 总边: {total}")
print(f"  composed: {composed}  ({composed/total*100:.1f}%)")
print(f"  hebbian:  {hebbian}  ({hebbian/total*100:.1f}%)")
print(f"  other:    {other}  ({other/total*100:.1f}%)")
print(f"  composed:hebbian = 1:{hebbian/max(composed,1):.1f}")
print("\nlabel 分布 top 10:")
for k, v in lab_em.most_common(10):
    print(f"  {k}: {v}")
print("\nother labels top 8:")
for k, v in other_labels.most_common(8):
    print(f"  {k}: {v}")

# emergent_edges.json 精确统计 (e=[src,label,target,kind])
ee = kg.get('emergent_edges', [])
print(f"\nemergent_edges.json 总条数: {len(ee)}")
ec = Counter()
for e in ee:
    if isinstance(e, (list, tuple)) and len(e) >= 2:
        ec[str(e[1]).lower()] += 1
for k, v in ec.most_common(12):
    print(f"  {k}: {v}")
