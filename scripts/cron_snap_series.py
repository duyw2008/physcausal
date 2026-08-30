#!/usr/bin/env python3
"""历史快照序列统一口径分析 (37855_exit / 38055 / 38255 / 38455)。"""
import json, gzip, glob, os

data_dir = os.path.expanduser('~/Agent/physcausal/data')

def load(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)

pairs = []
for kg_path in sorted(glob.glob(data_dir + '/evo_snapshot_gen*_kg.json*'), key=os.path.getmtime):
    nn_path = kg_path.replace('_kg.json', '_neural.json')
    if not os.path.exists(nn_path):
        continue
    pairs.append((kg_path, nn_path))

for kg_path, nn_path in pairs:
    kg = load(kg_path)
    nn = load(nn_path)
    gen = kg.get('generation', '?')
    edges = kg.get('edges', 0)
    K = nn.get('K', 0)
    cells = len(nn.get('cells', []))
    nv = kg.get('vs.graph', {}).get('node_vectors', {})
    concepts = len(nv) if hasattr(nv, '__len__') else None

    syn = nn.get('synaptic', {})
    acts = syn.get('activations', {})
    tiers = syn.get('tiers', {})
    s_gt_1 = 0
    for v in acts.values():
        if isinstance(v, dict) and isinstance(v.get('s'), (int, float)) and v['s'] > 1.0:
            s_gt_1 += 1
    t4 = sum(1 for v in tiers.values() if (v if isinstance(v, int) else v.get('tier', v)) == 4)

    vc = kg.get('vs.cache', {})
    vc_em = sum(1 for rec in vc.values() if isinstance(rec, dict)
                for key in ('effects', 'causes') for e in rec.get(key, []) or []
                if isinstance(e, (list, tuple)) and len(e) >= 3 and e[2] == 'emergent')

    print(f"gen={gen} edges={edges} K={K} edge/K={edges/K if K else 0:.2f} "
          f"cells={cells} concepts={concepts} syn_edges={len(acts)} s>1.0={s_gt_1} t4={t4} "
          f"vc_emergent={vc_em}")
