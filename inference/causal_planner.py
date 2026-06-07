"""
因果规划 — 从目标反推干预序列

核心:
  1. 反向搜索 — 从目标变量出发, 沿因果边反向追溯到起点
  2. 路径评分 — 优先低层置信、短路径、几何路径
  3. 可行性验证 — forbidden 方向和 tier 过滤

与 chain (正向传播) 互补:
  chain: mass → ? (如果改变mass会怎样)
  plan:  ? → mass (要达到mass在quantum域, 需要做什么)
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import heapq


def _build_reverse_graph() -> Dict[str, List[Tuple[str, str, str, int]]]:
    """
    构建反向因果图: effect → [(cause, law_name, domain, tier)]

    返回 {variable: [(causes_it, law, domain, tier)]}
    """
    from physics.laws import library
    from inference.counterfactual_chain import build_dependency_graph

    fwd = build_dependency_graph()
    rev = defaultdict(list)

    for law in library.list_all():
        tier = getattr(law, 'confidence_tier', 1)
        for src, dst in law.causal_direction:
            rev[dst].append((src, law.name, law.domain, tier))

    return dict(rev)


def _is_forbidden(variable: str, effect: str) -> bool:
    """检查 variable→effect 是否被任何定律禁止"""
    from physics.laws import library
    for law in library.list_all():
        for fd_src, fd_dst in law.forbidden_directions:
            if (fd_src.lower() in variable.lower() and
                fd_dst.lower() in effect.lower()):
                return True
    return False


def plan(start: str, target: str, max_depth: int = 5,
         max_tier: int = 4, max_paths: int = 10) -> List[Dict]:
    """
    从 start 到 target 的因果路径规划。

    Returns:
        [{path, length, tiers, domains, score, tier_breakdown}]
    """
    rev = _build_reverse_graph()

    if target not in rev:
        return []

    # Dijkstra-like search with tier-weighted costs
    heap = [(0, target, [target], [], [])]  # (cost, current, path, tiers, domains)
    found = []
    visited = set()

    while heap and len(found) < max_paths * 3:
        cost, current, path, tiers, domains = heapq.heappop(heap)

        if current == start:
            path_rev = list(reversed(path))
            # 找到一条路径
            found.append({
                "path": path_rev,
                "length": len(path_rev) - 1,
                "tiers": tiers,
                "domains": domains,
                "score": round(cost, 2),
                "tier_breakdown": _tier_summary(tiers),
            })
            continue

        if len(path) >= max_depth + 1:
            continue

        for cause, law_name, domain, tier in rev.get(current, []):
            if tier > max_tier:
                continue
            if _is_forbidden(cause, current):
                continue
            if cause in path:  # 避免环路
                continue

            # 代价: tier 越高代价越大
            step_cost = 1.0 + tier * 0.5
            new_cost = cost + step_cost
            heapq.heappush(heap, (
                new_cost, cause, path + [cause],
                tiers + [tier], domains + [domain]
            ))

    # 取最佳路径
    best = sorted(found, key=lambda x: x["score"])[:max_paths]
    return best


def _tier_summary(tiers: List[int]) -> str:
    if not tiers:
        return "none"
    counts = {}
    for t in tiers:
        counts[t] = counts.get(t, 0) + 1
    parts = []
    for t in sorted(counts):
        marks = {0: "◎", 1: "●", 2: "○", 3: "◇", 4: "?"}
        parts.append(f"{marks.get(t, '?')}×{counts[t]}")
    return " ".join(parts)


def plan_multi_target(start: str, targets: List[str],
                      max_depth: int = 5) -> Dict[str, List[Dict]]:
    """多目标规划: 从 start 到多个 target 的最优路径"""
    results = {}
    for t in targets:
        paths = plan(start, t, max_depth=max_depth)
        if paths:
            results[t] = paths
    return results


def format_plan(paths: List[Dict], start: str, target: str) -> str:
    """人类可读的规划报告"""
    if not paths:
        return f"  无可行路径: {start} → {target}"

    lines = [f"=== 因果规划: {start} → {target} ==="]
    lines.append(f"  找到 {len(paths)} 条路径")
    lines.append("")

    for i, p in enumerate(paths[:5]):
        tier_str = p["tier_breakdown"]
        domains = " → ".join(p["domains"])
        lines.append(f"  {i+1}. 代价={p['score']:.1f}  长度={p['length']}  层级={tier_str}")
        lines.append(f"     路径: {' → '.join(p['path'])}")
        lines.append(f"     领域: {domains}")
        lines.append("")

    return "\n".join(lines)


def find_bridge_paths(start_domain: str, target_domain: str) -> List[Dict]:
    """
    找两个领域之间的桥接路径。
    从 start_domain 的变量出发, 到 target_domain 的变量。
    """
    from physics.laws import library
    start_vars = set()
    target_vars = set()
    for law in library.list_all():
        if law.domain == start_domain:
            start_vars.update(law.inputs + law.outputs)
        if law.domain == target_domain:
            target_vars.update(law.inputs + law.outputs)

    all_paths = []
    for sv in list(start_vars)[:5]:
        for tv in list(target_vars)[:5]:
            paths = plan(sv, tv, max_depth=4)
            for p in paths:
                p["start_var"] = sv
                p["target_var"] = tv
                all_paths.append(p)

    return sorted(all_paths, key=lambda x: x["score"])[:10]
