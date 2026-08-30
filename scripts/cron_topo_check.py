#!/usr/bin/env python3
"""费曼脑 cron 拓扑体检 — 读最新 kg/neural 快照, 按用户指定基线对比。"""
import json, gzip, glob, os

data_dir = os.path.expanduser('~/Agent/physcausal/data')

def load(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)

kg_files = sorted(glob.glob(data_dir + '/evo_snapshot_gen*_kg.json*'), key=os.path.getmtime)
nn_files = sorted(glob.glob(data_dir + '/evo_snapshot_gen*_neural.json*'), key=os.path.getmtime)
kg_path = kg_files[-1]
nn_path = nn_files[-1]
kg = load(kg_path)
nn = load(nn_path)
gen = kg.get('generation', nn.get('generation', '?'))
print(f"快照: gen={gen} kg={os.path.basename(kg_path)} nn={os.path.basename(nn_path)}")

# --- 规模 ---
edges = kg.get('edges', 0)
K = nn.get('K', 0)
cells = len(nn.get('cells', []))
edge_K = edges / K if K else 0

# --- 概念节点 (vs.graph node_vectors) ---
nv = kg.get('vs.graph', {}).get('node_vectors', {})
concepts = len(nv) if hasattr(nv, '__len__') else None

# --- 突触层: activations (s值), tiers ---
syn = nn.get('synaptic', {})
acts = syn.get('activations', {})
tiers = syn.get('tiers', {})
n_syn = len(acts)
s_gt_1 = 0
s_vals = []
for v in acts.values():
    if isinstance(v, dict) and 's' in v:
        s_vals.append(v['s'])
        if v['s'] > 1.0:
            s_gt_1 += 1
tier_counts = {}
for v in tiers.values():
    t = v if isinstance(v, int) else v.get('tier', v)
    tier_counts[t] = tier_counts.get(t, 0) + 1
t4 = tier_counts.get(4, 0)

# --- vs.cache emergent ---
vc = kg.get('vs.cache', {})
vc_em = 0
vc_composed = 0
vc_hebbian = 0
vc_total = 0
vc_nodes = len(vc)
for node, rec in vc.items():
    if not isinstance(rec, dict):
        continue
    for key in ('effects', 'causes'):
        for e in rec.get(key, []) or []:
            vc_total += 1
            if isinstance(e, (list, tuple)) and len(e) >= 3 and 'emergent' in str(e[2]):
                vc_em += 1
                label = str(e[1]).lower()
                if 'composed' in label:
                    vc_composed += 1
                elif 'hebbian' in label:
                    vc_hebbian += 1

# --- emergent_edges 明细 (kg) ---
ee = kg.get('emergent_edges', [])
ee_total = len(ee)
ee_composed = ee_hebbian = ee_sleep = ee_other = 0
for e in ee:
    if not isinstance(e, (list, tuple)) or len(e) < 2:
        continue
    t = str(e[1]).lower()
    if 'composed' in t:
        ee_composed += 1
    elif 'hebbian' in t:
        ee_hebbian += 1
    elif 'sleep' in t:
        ee_sleep += 1
    else:
        ee_other += 1

out = {
    'gen': gen, 'edges': edges, 'K': K, 'edge_K': round(edge_K, 1),
    'cells': cells, 'concepts': concepts,
    'syn_edges': n_syn, 's_gt_1': s_gt_1,
    's_p50': round(sorted(s_vals)[len(s_vals)//2], 3) if s_vals else None,
    's_max': round(max(s_vals), 3) if s_vals else None,
    'tier_counts': dict(sorted(tier_counts.items())),
    't4': t4,
    'vc_nodes': vc_nodes, 'vc_total_edges': vc_total,
    'vc_emergent': vc_em, 'vc_composed': vc_composed, 'vc_hebbian': vc_hebbian,
    'ee_total': ee_total, 'ee_composed': ee_composed, 'ee_hebbian': ee_hebbian,
    'ee_sleep': ee_sleep, 'ee_other': ee_other,
}
print(json.dumps(out, ensure_ascii=False, indent=1))
