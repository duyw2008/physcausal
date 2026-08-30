#!/usr/bin/env python3
"""拓扑健康体检:完整指标计算。"""
import json, gzip, glob, os

data_dir = os.path.expanduser('~/Agent/physcausal/data')

def load(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)

kg_files = sorted(glob.glob(os.path.join(data_dir, 'evo_snapshot_gen*_kg.json')))
neural_files = sorted(glob.glob(os.path.join(data_dir, 'evo_snapshot_gen*_neural.json')))
kg = load(kg_files[-1])
nn = load(neural_files[-1])
gen = kg['generation']
ts = kg['timestamp']

# --- 结构探查 ---
syn = nn['synaptic']
print("synaptic keys:", list(syn.keys()))
print("synaptic.tiers type:", type(syn['tiers']))
if isinstance(syn['tiers'], dict):
    print("tiers keys:", list(syn['tiers'].keys())[:20])
    for k, v in syn['tiers'].items():
        print(f"  tier {k}: type={type(v).__name__}", f"len={len(v)}" if hasattr(v, '__len__') else v)
print("synaptic.activations type:", type(syn['activations']))
print("synaptic.retrograde type:", type(syn['retrograde']))

print("\n--- vs.cache ---")
vc = kg['vs.cache']
print("vs.cache type:", type(vc))
if isinstance(vc, dict):
    n_em = 0
    for k, v in vc.items():
        if isinstance(v, list):
            print(f"  {k}: list len={len(v)} sample={v[0] if v else None}")
            for e in v:
                if isinstance(e, dict) and 'emergent' in str(e):
                    n_em += 1
        else:
            print(f"  {k}: {type(v).__name__} {str(v)[:120]}")
    print("vs.cache emergent-ish:", n_em)

print("\n--- emergent_edges ---")
ee = kg['emergent_edges']
print("len:", len(ee))
print("sample entries:", ee[:3])
types = {}
for e in ee:
    # 探索元素结构
    if isinstance(e, list):
        t = e[1] if len(e) > 1 else '?'
        types[t] = types.get(t, 0) + 1
    elif isinstance(e, dict):
        t = e.get('type', e.get('kind', '?'))
        types[t] = types.get(t, 0) + 1
print("emergent types:", types)

print("\n--- edges ---")
edges = kg['edges']
print("edges type:", type(edges), "len:", len(edges) if hasattr(edges, '__len__') else '?')
if isinstance(edges, list) and edges:
    print("edge sample:", edges[0])
    print("edge sample2:", edges[1])
elif isinstance(edges, dict):
    ks = list(edges.keys())[:10]
    print("edges keys sample:", ks)
    for k in ks[:3]:
        print(f"  {k}: {str(edges[k])[:150]}")

print("\n--- vs.graph ---")
vg = kg['vs.graph']
print("dim:", vg.get('dim'))
print("node_vectors type:", type(vg.get('node_vectors')))
nv = vg.get('node_vectors')
if isinstance(nv, dict):
    print("node_vectors keys:", len(nv), list(nv.keys())[:10])

print("\n--- cells ---")
cells = nn['cells']
print("cells:", len(cells))
print("K:", nn['K'])
