#!/usr/bin/env python3
"""emergent 边类型分布 + 口径核对"""
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

gen = sys.argv[1] if len(sys.argv) > 1 else '39271'
kg = load_snap(gen, 'kg')
vc = kg.get('vs.cache', {})

type_by_domain = Counter()
em_types = Counter()
em_domains = Counter()
em_slot = Counter()
samples = []
for node, rec in vc.items():
    for slot in ('effects', 'causes'):
        for e in rec.get(slot, []):
            if len(e) >= 3:
                etype, target, domain = e[0], e[1], e[2]
                type_by_domain[(etype, domain)] += 1
                if domain == 'emergent':
                    em_types[etype] += 1
                    em_domains[domain] += 1
                    em_slot[slot] += 1
                    if len(samples) < 8:
                        samples.append((node, slot, e))

print(f'=== gen {gen} vs.cache (type, domain) 分布 top15 ===')
for (t, d), c in type_by_domain.most_common(15):
    print(f'  {t:28s} | {d:22s} | {c}')
print()
print('=== emergent domain 边: 类型分布 ===')
for t, c in em_types.most_common():
    print(f'  {t}: {c}')
print('  slot:', dict(em_slot))
print('  样本:')
for s in samples:
    print('   ', str(s)[:110])
