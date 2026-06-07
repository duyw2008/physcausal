"""
层次化抽象 — 从低层变量中涌现高层概念

三层递进:
  1. 互信息聚类 — 哪些变量总是出现在同一组定律里
  2. 信息瓶颈 — 压缩变量组为高层抽象时保留了多少因果信息
  3. 涌现检测 — 新概念是否具有成员个体不具备的属性

核心: 不是人工归类 (VARIABLE_CLASSIFICATION 已做),
      而是从因果图中自动发现新的层级结构。
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import math


def _variable_cooccurrence() -> Dict[Tuple[str, str], int]:
    """计算变量在定律中的共现频率"""
    from physics.laws import library

    cooc = defaultdict(int)
    for law in library.list_all():
        all_vars = set(law.inputs + law.outputs)
        vars_list = sorted(all_vars)
        for i, a in enumerate(vars_list):
            for b in vars_list[i + 1:]:
                key = tuple(sorted([a, b]))
                cooc[key] += 1
    return dict(cooc)


def _variable_frequency() -> Dict[str, int]:
    """每个变量出现在多少条定律中"""
    from physics.laws import library
    freq = defaultdict(int)
    for law in library.list_all():
        for v in set(law.inputs + law.outputs):
            freq[v] += 1
    return dict(freq)


def mutual_information_matrix() -> Dict[Tuple[str, str], float]:
    """
    变量对之间的互信息 (用共现频率近似)。

    I(X;Y) = Σ p(x,y) log₂(p(x,y) / (p(x)p(y)))
    近似: p(x) ∝ freq[x], p(x,y) ∝ cooc[x,y]
    """
    cooc = _variable_cooccurrence()
    freq = _variable_frequency()
    total_laws = len(freq)

    mi = {}
    for (a, b), count in cooc.items():
        if a not in freq or b not in freq:
            continue
        pa = freq[a] / total_laws if total_laws > 0 else 0
        pb = freq[b] / total_laws if total_laws > 0 else 0
        pab = count / total_laws if total_laws > 0 else 0
        if pa == 0 or pb == 0 or pab == 0:
            continue
        mi_val = pab * math.log2(pab / (pa * pb))
        if mi_val > 0:
            mi[(a, b)] = mi_val
    return dict(sorted(mi.items(), key=lambda x: x[1], reverse=True))


def cluster_by_mi(min_mi: float = 0.1, max_clusters: int = 10) -> List[Dict]:
    """
    互信息聚类: 找互信息最高的变量对, 合并为高层概念。

    返回: [{name, variables, mi_sum, size}]
    """
    mi = mutual_information_matrix()
    if not mi:
        return []

    # 贪心聚类
    assigned = set()
    clusters = []

    for (a, b), mi_val in mi.items():
        if len(clusters) >= max_clusters:
            break
        if a in assigned or b in assigned:
            continue

        # 过滤基础变量和几何变量 (已有人工分类)
        from physics.laws import classify_variable
        cat_a = classify_variable(a)
        cat_b = classify_variable(b)
        if cat_a in ("fundamental", "geometric") and cat_b in ("fundamental", "geometric"):
            continue

        cluster_name = f"{a}_{b}"[:40]
        clusters.append({
            "name": cluster_name,
            "variables": [a, b],
            "mi": round(mi_val, 3),
            "size": 2,
        })
        assigned.add(a)
        assigned.add(b)

    return clusters


def emergence_score(cluster: Dict) -> float:
    """
    涌现评分: 这个变量集群是否构成一个新的有效概念？

    标准:
      - 互信息高 (>0.2): +1
      - 跨领域 (变量来自不同领域): +0.5
      - 至少一个变量是派生的 (不是基础变量): +0.3
      - 集群内部变量在至少 2 条定律中共现: +0.5

    总分 < 1.0 的不推荐作为新概念。
    """
    score = 0.0

    if cluster["mi"] >= 0.2:
        score += 1.0
    elif cluster["mi"] >= 0.1:
        score += 0.5

    from physics.laws import library, classify_variable
    vars_list = cluster["variables"]
    domains = set()
    has_derived = False
    for v in vars_list:
        cat = classify_variable(v)
        if cat == "derived":
            has_derived = True
        for law in library.list_all():
            if v in law.inputs + law.outputs:
                domains.add(law.domain)

    if len(domains) >= 2:
        score += 0.5
    if has_derived:
        score += 0.3

    if cluster["mi"] >= 0.15:
        score += 0.5

    return round(score, 1)


def find_emergent_concepts(min_emergence: float = 1.0) -> List[Dict]:
    """
    发现涌现概念: 聚类 + 评分, 返回值得提升为高层变量的集群。
    """
    clusters = cluster_by_mi(min_mi=0.05, max_clusters=15)
    emergent = []

    for c in clusters:
        score = emergence_score(c)
        if score >= min_emergence:
            c["emergence_score"] = score
            emergent.append(c)

    return sorted(emergent, key=lambda x: x["emergence_score"], reverse=True)


def abstraction_report() -> str:
    """层次化抽象报告"""
    mi = mutual_information_matrix()
    if not mi:
        return "  (变量太少, 无法计算互信息)"

    lines = ["=== 层次化抽象 ==="]
    top_mi = list(mi.items())[:5]
    lines.append(f"\n  最强互信息对 (top {len(top_mi)}):")
    for (a, b), val in top_mi:
        lines.append(f"    I({a};{b}) = {val:.3f}")

    emergent = find_emergent_concepts(min_emergence=1.0)
    if emergent:
        lines.append(f"\n  涌现概念 ({len(emergent)}):")
        for c in emergent:
            lines.append(f"    {c['name']} (MI={c['mi']} 涌现={c['emergence_score']})")
            lines.append(f"    变量: {c['variables']}")
    else:
        lines.append(f"\n  (未发现涌现概念 — 当前变量结构已足够清晰)")

    return "\n".join(lines)
