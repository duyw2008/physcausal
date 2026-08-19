#!/usr/bin/env python3
"""定律库因果方向 → KG 边注入（给路径不给 tier）

把 laws.py 的 causal_direction 转成 KG 的 causes/effects 边，domain 统一标 "physics"。
- VSA 的 DOMAINS 含 "physics"（不会 fallback 到 emergent）
- _rebuild_cache 的 _CAUSAL_DOMAINS 含 "physics"（细胞读图时优先走）
- _consume_one 里只有 "axomatic" 才标 tier2 → "physics" 域只给路径不给结论

脑消费后自然行走 → Hebbian 强化 → δS=0 闸门验证 → 晋升，结构从学习中涌现。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from physics.laws import library
from meta_cognition.feed_queue import FeedQueue

q = FeedQueue()

concepts = {}
edges = []
for law in library._laws:
    # 概念 = inputs + outputs + causal_direction 两端（过滤单字符公式变量如 x/r/m）
    for var in set(law.inputs + law.outputs):
        if len(var) > 1:
            concepts[var] = law.name
    for src, dst in law.causal_direction:
        if len(src) > 1:
            concepts[src] = law.name
        if len(dst) > 1:
            concepts[dst] = law.name
        edges.append((src, dst, law.name))

for name in sorted(concepts):
    q.feed_concept(name, source="laws_library", domain="physics")

for src, dst, law_name in edges:
    q.feed_edge(src, dst, law_name, source="laws_library",
                domain="physics", initial_s=0.05)

print(f"注入 {len(concepts)} 概念 + {len(edges)} 因果边（domain=physics，只给路径不给 tier）")
print("脑将在下个 breathe 周期消费，自然行走、强化、δS=0 验证、晋升")
