#!/usr/bin/env python3
"""精确统计 vs.cache emergent 边 composed/hebbian（effects 用 e[0], causes 用 e[1]）。
对比 gen37512_exit 与 gen37912 两次快照。"""
import json, gzip
from collections import Counter

def load(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)

def analyze(kg_path, label):
    kg = load(kg_path)
    vc = kg['vs.cache']
    lab_em = Counter()
    composed = hebbian = other = 0
    for node, rec in vc.items():
        if not isinstance(rec, dict):
            continue
        for e in rec.get('effects', []) or []:
            if isinstance(e, (list, tuple)) and len(e) >= 3 and e[2] == 'emergent':
                lab = str(e[0]).lower()
                lab_em[lab] += 1
                if 'composed' in lab: composed += 1
                elif 'hebbian' in lab: hebbian += 1
                else: other += 1
        for e in rec.get('causes', []) or []:
            if isinstance(e, (list, tuple)) and len(e) >= 3 and e[2] == 'emergent':
                lab = str(e[1]).lower()
                lab_em[lab] += 1
                if 'composed' in lab: composed += 1
                elif 'hebbian' in lab: hebbian += 1
                else: other += 1
    total = sum(lab_em.values())
    print(f"=== {label} ===")
    print(f"vs.cache emergent(e[2]=='emergent' 精确): {total}")
    print(f"  composed: {composed}  ({composed/total*100:.1f}%)" if total else "  composed: 0")
    print(f"  hebbian:  {hebbian}  ({hebbian/total*100:.1f}%)" if total else "  hebbian: 0")
    print(f"  other:    {other}")
    if composed:
        print(f"  composed:hebbian = 1:{hebbian/max(composed,1):.1f}")
    print("  label top8:", dict(lab_em.most_common(8)))
    print()

analyze('/home/duyw/Agent/physcausal/data/evo_snapshot_gen37512_exit_kg.json', 'gen37512_exit (上次体检快照)')
analyze('/home/duyw/Agent/physcausal/data/evo_snapshot_gen37912_kg.json', 'gen37912 (当前快照)')
