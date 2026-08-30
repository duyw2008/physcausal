#!/usr/bin/env python3
"""费曼脑拓扑体检 - 快照指标计算"""
import gzip, json, os, sys

DATA = os.path.expanduser('~/Agent/physcausal/data')

def load_snap(gen, kind):
    path = os.path.join(DATA, f'evo_snapshot_gen{gen}_{kind}.json')
    if not os.path.exists(path):
        path = path + '.gz'
    if not os.path.exists(path):
        # try plain json
        for suffix in ('', '.gz'):
            p = os.path.join(DATA, f'evo_snapshot_gen{gen}_exit_{kind}.json{suffix}')
            if os.path.exists(p):
                path = p; break
    print(f'  loading {os.path.basename(path)}', file=sys.stderr)
    # 快照均为 gzip 压缩(伪装 .json),用魔数探测
    with open(path, 'rb') as f:
        magic = f.read(2)
    opener = gzip.open if magic == b'\x1f\x8b' else open
    with opener(path, 'rt', encoding='utf-8') as f:
        return json.load(f)

def main():
    gen = sys.argv[1] if len(sys.argv) > 1 else '39271'
    kg = load_snap(gen, 'kg')
    neu = load_snap(gen, 'neural')

    print(f'=== gen {gen} ===')
    print('KG keys:', list(kg.keys()) if isinstance(kg, dict) else type(kg))
    print('NEU keys:', list(neu.keys()) if isinstance(neu, dict) else type(neu))

    # ---- KG stats ----
    kg_nodes = set()
    kg_edges = 0
    edge_list = kg.get('edges', []) if isinstance(kg, dict) else []
    if isinstance(kg, dict):
        for k, v in kg.items():
            if isinstance(v, list):
                print(f'  kg.{k}: list[{len(v)}]', end='')
                if v: print(f' sample={str(v[0])[:120]}', end='')
                print()
    if edge_list:
        for e in edge_list:
            if isinstance(e, (list, tuple)) and len(e) >= 2:
                kg_nodes.add(str(e[0])); kg_nodes.add(str(e[1]))
        kg_edges = len(edge_list)
        print(f'kg.edges: {kg_edges}, distinct nodes: {len(kg_nodes)}')
        print(f'edge sample: {str(edge_list[0])[:150]}')

    # ---- Neural stats ----
    syn = neu.get('synapses') or neu.get('synaptic_memory') or neu.get('syn_edges') or []
    print(f'NEU synapse container: {len(syn)} items')
    if syn:
        print(f'  sample: {str(syn[0])[:200]}')

if __name__ == '__main__':
    main()
