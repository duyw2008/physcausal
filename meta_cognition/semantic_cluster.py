"""
变量语义聚类 — 从模糊表达中提炼核心概念

两个维度:
  1. 名称相似度 — 编辑距离 / 公共子串
  2. 因果邻居相似度 — 图结构中连接模式相同

两个信号都强 → 可能是同一概念的不同名字。
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import re


def _normalize(name: str) -> str:
    """去掉下划线和数字, 统一小写"""
    return re.sub(r'[_\d]+', '', name.lower())


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein 距离"""
    if len(a) < len(b):
        a, b = b, a
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def name_similarity(a: str, b: str) -> float:
    """名称相似度 0-1"""
    na = _normalize(a)
    nb = _normalize(b)
    if na == nb:
        return 1.0
    max_len = max(len(na), len(nb))
    if max_len == 0:
        return 1.0
    dist = _edit_distance(na, nb)
    return 1.0 - dist / max_len


def _causal_neighborhood(variable: str) -> Tuple[Set[str], Set[str]]:
    """变量的因果邻居: (上游变量, 下游变量)"""
    from inference.counterfactual_chain import build_dependency_graph
    graph = build_dependency_graph()
    node = graph.get(variable, {"as_input": [], "as_output": []})
    upstream = {v for _, v, _ in node.get("as_input", [])}
    downstream = {v for _, v, _ in node.get("as_output", [])}
    return upstream, downstream


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(len(a | b), 1)


def neighbor_similarity(a: str, b: str) -> float:
    """因果邻居相似度 0-1"""
    up_a, down_a = _causal_neighborhood(a)
    up_b, down_b = _causal_neighborhood(b)
    up_sim = _jaccard(up_a, up_b)
    down_sim = _jaccard(down_a, down_b)
    return (up_sim + down_sim) / 2


def find_semantic_clusters(min_name_sim: float = 0.4,
                           min_neighbor_sim: float = 0.3,
                           min_combined: float = 0.5) -> List[Dict]:
    """
    找语义相关的变量群。

    返回: [{variables: [a,b], name_sim, neighbor_sim, combined, suggestion}]
    """
    from physics.laws import library
    # 收集所有变量
    all_vars = set()
    for law in library.list_all():
        all_vars.update(law.inputs + law.outputs)

    # 过滤太短的
    vars_list = [v for v in sorted(all_vars) if len(v) >= 2]

    clusters = []
    seen_pairs = set()

    for i, a in enumerate(vars_list):
        for b in vars_list[i + 1:]:
            key = tuple(sorted([a, b]))
            if key in seen_pairs:
                continue
            seen_pairs.add(key)

            name_sim = name_similarity(a, b)
            if name_sim < min_name_sim:
                continue

            neighbor_sim = neighbor_similarity(a, b)
            if neighbor_sim < min_neighbor_sim:
                continue

            combined = name_sim * 0.6 + neighbor_sim * 0.4
            if combined < min_combined:
                continue

            suggestion = None
            if name_sim > 0.8 and neighbor_sim > 0.5:
                suggestion = "strong_merge"  # 几乎肯定是同一概念
            elif name_sim > 0.6:
                suggestion = "likely_related"  # 名字像, 邻居部分相似
            elif neighbor_sim > 0.5:
                suggestion = "functional_equivalent"  # 名字不像但因果角色相同

            clusters.append({
                "variables": [a, b],
                "name_sim": round(name_sim, 2),
                "neighbor_sim": round(neighbor_sim, 2),
                "combined": round(combined, 2),
                "suggestion": suggestion,
            })

    return sorted(clusters, key=lambda x: x["combined"], reverse=True)


def cluster_report() -> str:
    """语义聚类报告"""
    clusters = find_semantic_clusters()
    if not clusters:
        return "  ✓ 未发现需要合并的变量"

    lines = ["=== 变量语义聚类 ==="]
    lines.append(f"发现 {len(clusters)} 对可能相关的变量:")

    strong = [c for c in clusters if c["suggestion"] == "strong_merge"]
    likely = [c for c in clusters if c["suggestion"] == "likely_related"]
    functional = [c for c in clusters if c["suggestion"] == "functional_equivalent"]

    if strong:
        lines.append(f"\n  强合并 ({len(strong)} 对, 建议自动合并):")
        for c in strong:
            lines.append(f"    {c['variables'][0]} ↔ {c['variables'][1]} (名称={c['name_sim']:.0%} 邻居={c['neighbor_sim']:.0%})")

    if likely:
        lines.append(f"\n  可能相关 ({len(likely)} 对, 建议人工审核):")
        for c in likely:
            lines.append(f"    {c['variables'][0]} ↔ {c['variables'][1]} (名称={c['name_sim']:.0%} 邻居={c['neighbor_sim']:.0%})")

    if functional:
        lines.append(f"\n  功能等价 ({len(functional)} 对, 因果角色相同但名字不同):")
        for c in functional:
            lines.append(f"    {c['variables'][0]} ↔ {c['variables'][1]} (名称={c['name_sim']:.0%} 邻居={c['neighbor_sim']:.0%})")

    return "\n".join(lines)
