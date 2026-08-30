#!/usr/bin/env python3
"""费曼脑拓扑体检 - 完整指标(与历史报告口径一致)"""
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
    raise FileNotFoundError(f'no snapshot gen {gen} {kind}')

def metrics(gen):
    kg = load_snap(gen, 'kg')
    neu = load_snap(gen, 'neural')

    # ---- vs.cache 边 ----
    vc = kg.get('vs.cache', {})
    vc_edges = []          # (type, target, domain)
    vc_total = 0
    vc_emergent = 0
    vc_em_composed = 0
    vc_em_hebbian = 0
    vc_em_other = 0
    for node, rec in vc.items():
        for slot in ('effects', 'causes'):
            for e in rec.get(slot, []):
                if len(e) >= 3:
                    vc_total += 1
                    etype, target, domain = e[0], e[1], e[2]
                    vc_edges.append((etype, target, domain))
                    if domain == 'emergent':
                        vc_emergent += 1
                        if etype == 'composed_shortcut':
                            vc_em_composed += 1
                        elif etype == 'hebbian_shortcut':
                            vc_em_hebbian += 1
                        else:
                            vc_em_other += 1

    # ---- emergent_edges 明细 ----
    ee = kg.get('emergent_edges', [])
    ee_composed = sum(1 for e in ee if len(e) >= 2 and e[1] == 'composed_shortcut')
    ee_hebbian = sum(1 for e in ee if len(e) >= 2 and e[1] == 'hebbian_shortcut')
    ee_other = len(ee) - ee_composed - ee_hebbian

    # ---- 突触 ----
    act = neu.get('synaptic', {}).get('activations', {})
    tiers = neu.get('synaptic', {}).get('tiers', {})
    n_syn = len(act)
    s_gt1 = sum(1 for v in act.values() if v.get('s', 0) > 1.0)
    s_vals = [v.get('s', 0) for v in act.values()]
    s_med = sorted(s_vals)[len(s_vals)//2] if s_vals else 0
    t4 = sum(1 for v in tiers.values() if v == 4)
    t_vals = Counter(tiers.values())

    # ---- 概念 / 细胞 ----
    K = neu.get('K')
    cells = len(neu.get('cells', []))
    node_vec = kg.get('vs.graph', {}).get('node_vectors', {})
    vg_nodes = len(node_vec)

    return {
        'gen': gen,
        'kg_edges': kg.get('edges'),
        'K': K,
        'edge_per_K': round(kg.get('edges', 0) / (K or 1), 3),
        'vc_total': vc_total,
        'vc_emergent': vc_emergent,
        'vc_em_composed': vc_em_composed,
        'vc_em_hebbian': vc_em_hebbian,
        'vc_em_other': vc_em_other,
        'ee_total': len(ee),
        'ee_composed': ee_composed,
        'ee_hebbian': ee_hebbian,
        'ee_other': ee_other,
        'syn_total': n_syn,
        's_gt1': s_gt1,
        's_gt1_pct': round(100*s_gt1/n_syn, 1) if n_syn else 0,
        's_median': s_med,
        'tier4': t4,
        'tiers': dict(t_vals.most_common()),
        'cells': cells,
        'vs_graph_nodes': vg_nodes,
    }

def main():
    gens = sys.argv[1:] or ['38471', '39271']
    out = []
    for g in gens:
        print(f'-- computing gen {g} --', file=sys.stderr)
        out.append(metrics(g))
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == '__main__':
    main()
