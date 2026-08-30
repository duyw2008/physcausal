#!/usr/bin/env python3
"""提取 vs.cache 拓扑指标 + emergent_edges 模式分布"""
import json, gzip, os, collections

DATA = os.path.expanduser('~/Agent/physcausal/data')
latest_kg = os.path.join(DATA, 'evo_snapshot_gen39455_kg.json')
with gzip.open(latest_kg, 'rt', encoding='utf-8') as f:
    kg = json.load(f)

cache = kg['vs.cache']
print(f"vs.cache 概念节点数: {len(cache)}")

total_eff = 0
total_cau = 0
edge_types = collections.Counter()
srcs = set()
dsts = set()
# effects/causes 元素结构: ['src','dst','mode'] 或 ['src','dst',...,'mode']
sample = None
for node, val in cache.items():
    eff = val.get('effects', [])
    cau = val.get('causes', [])
    total_eff += len(eff)
    total_cau += len(cau)
    for e in eff:
        edge_types['effects:' + str(e[-1] if isinstance(e, list) else e)] += 1
        if sample is None:
            sample = e
    for e in cau:
        edge_types['causes:' + str(e[-1] if isinstance(e, list) else e)] += 1

print(f"effects 总数: {total_eff}, causes 总数: {total_cau}, 合计: {total_eff+total_cau}")
print(f"边/K比 = {(total_eff+total_cau)/len(cache):.1f}")
print("边类型分布(top 15):")
for k, v in edge_types.most_common(15):
    print(f"  {k}: {v}")
print("样本 effects 元素:", sample)

# emergent_edges 模式分布
em = kg['emergent_edges']
print(f"\nemergent_edges 总数: {len(em)}")
modes = collections.Counter()
len_dist = collections.Counter()
for e in em:
    len_dist[len(e)] += 1
    modes[e[-1]] += 1
print("emergent_edges 长度分布:", dict(len_dist))
print("mode 分布:", dict(modes))

# 样本各种模式
by_mode = collections.defaultdict(list)
for e in em:
    by_mode[e[-1]].append(e)
for m, lst in by_mode.items():
    print(f"\n  mode={m} 样本: {lst[0]}")
