#!/usr/bin/env python3
"""费曼脑拓扑体检 - 完整指标计算(与历史报告口径一致)"""
import gzip, json, os, sys
from collections import Counter

DATA = os.path.expanduser('~/Agent/physcausal/data')

def load_snap(gen, kind):
    path = os.path.join(DATA, f'evo_snapshot_gen{gen}_{kind}.json')
    if not os.path.exists(path):
        path = os.path.join(DATA, f'evo_snapshot_gen{gen}_exit_{kind}.json')
    with open(path, 'rb') as f:
        magic = f.read(2)
    opener = gzip.open if magic == b'\x1f\x8b' else open
    with opener(path, 'rt', encoding='utf-8') as f:
        return json.load(f)

def main():
    gen = sys.argv[1] if len(sys.argv) > 1 else '39271'
    kg = load_snap(gen, 'kg')
    neu = load_snap(gen, 'neural')

    print(f'=== gen {gen} | kg.gen={kg.get("generation")} neu.gen={neu.get("generation")} ===')

    # ---- 概念节点 / 边 ----
    edges = kg.get('edges')
    vs_graph = kg.get('vs.graph', {})
    vs_cache = kg.get('vs.cache', {})
    print(f'kg.edges = {edges} (type {type(edges).__name__})')
    print(f'vs.graph type={type(vs_graph).__name__} len={len(vs_graph)}')
    print(f'vs.cache type={type(vs_cache).__name__} len={len(vs_cache)}')
    if isinstance(vs_graph, dict):
        keys = list(vs_graph.keys())[:3]
        for k in keys:
            print(f'  vs.graph[{k!r}] = {str(vs_graph[k])[:150]}')
    if isinstance(vs_cache, dict):
        keys = list(vs_cache.keys())[:3]
        for k in keys:
            print(f'  vs.cache[{k!r}] = {str(vs_cache[k])[:200]}')

    # ---- NEU ----
    K = neu.get('K')
    cells = neu.get('cells')
    syn = neu.get('synaptic', {})
    print(f'neu.K = {K} (type {type(K).__name__})')
    print(f'neu.cells = {len(cells) if hasattr(cells,"__len__") else cells}')
    print(f'neu.synaptic type={type(syn).__name__} len={len(syn)}')
    if isinstance(syn, dict):
        keys = list(syn.keys())[:8]
        for k in keys:
            v = syn[k]
            print(f'  synaptic[{k!r}] = {str(v)[:120]}')
    elif isinstance(syn, list) and syn:
        print(f'  synaptic[0] = {str(syn[0])[:200]}')
    shelf = neu.get('cell_shelf', {})
    print(f'cell_shelf type={type(shelf).__name__} len={len(shelf)}')

if __name__ == '__main__':
    main()
