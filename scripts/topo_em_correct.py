#!/usr/bin/env python3
"""修正口径: effects 用 e[0] 作 label, causes 用 e[1] 作 label"""
import gzip, json, os, sys
from collections import Counter

DATA = os.path.expanduser('~/Agent/physcausal/data')

def load_snap(gen, kind):
    for fname in (f'evo_snapshot_gen{gen}_{kind}.json', f'evo_snapshot_gen{gen}_exit_{kind}.json'):
        path = os.path.join(DATA, fname)
        if os.path.exists(path):
            with open(path, 'rb') as f:
                magic = f.read(2)
            opener = gzip.open if magic == b'\x1f\x8b' else open
            with opener(path, 'rt', encoding='utf-8') as f:
                return json.load(f)

for gen in sys.argv[1:] or ['38471', '39271']:
    kg = load_snap(gen, 'kg')
    vc = kg.get('vs.cache', {})
    em = Counter()
    slot_fmt = Counter()
    for node, rec in vc.items():
        for slot in ('effects', 'causes'):
            for e in rec.get(slot, []):
                if len(e) >= 3:
                    label = e[0] if slot == 'effects' else e[1]
                    domain = e[2]
                    slot_fmt[(slot, len(e))] += 1
                    if domain == 'emergent':
                        em[label] += 1
    total = sum(em.values())
    comp = em.get('composed_shortcut', 0)
    hebb = em.get('hebbian_shortcut', 0)
    other = total - comp - hebb
    print(f'=== gen {gen}: vs.cache emergent 边(修正口径) ===')
    print(f'  total={total} composed={comp} hebbian={hebb} other={other}')
    print(f'  composed%={100*comp/total:.1f}%  hebbian%={100*hebb/total:.1f}%  比=1:{hebb/max(comp,1):.2f}')
    print(f'  slot 格式分布: {dict(slot_fmt.most_common(6))}')
    # 实时 emergent_edges 明细(直接文件)
    ee = kg.get('emergent_edges', [])
    eec = Counter(e[1] if len(e) > 1 else '?' for e in ee)
    print(f'  emergent_edges 明细: total={len(ee)} composed={eec.get("composed_shortcut",0)} hebbian={eec.get("hebbian_shortcut",0)}')
