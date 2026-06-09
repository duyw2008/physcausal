"""
因果链类比发现 — 跨域结构联想 (v2: 软匹配)

用结构相似度代替精确签名匹配,
让物理学家可以自动发现"耗散 ≈ 退相干"这类深层类比。
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Set
from collections import defaultdict


def _chain_profile(chain: List[Dict]) -> Dict:
    """提取因果链的结构剖面"""
    domains = []
    end_types = set()
    depth = 0
    branch_count = 0

    for step in chain:
        if "error" in step:
            continue
        dom = step.get("domain", "?")[:3]
        domains.append(dom)
        eff = step.get("effect_variable", "")
        d = step.get("depth", 0)
        if d > depth:
            depth = d

        if "entropy" in eff or "temperature" in eff or "order" in eff:
            end_types.add("THM")
        elif "state" in eff or "coupling" in eff or "collapse" in eff:
            end_types.add("STA")
        elif "force" in eff or "energy" in eff:
            end_types.add("ENE")
        elif "geodesic" in eff or "curvature" in eff:
            end_types.add("GEO")
        elif "wave" in eff or "amplitude" in eff:
            end_types.add("QNT")
        else:
            end_types.add("GEN")

    length = sum(1 for s in chain if "error" not in s)
    domain_set = set(domains)

    return {
        "length": length,
        "depth": depth,
        "domains": domain_set,
        "end_types": end_types,
        "domain_seq": "/".join(domains),
    }


def _chain_similarity(pa: Dict, pb: Dict) -> float:
    """计算两条因果链的结构相似度 (0-1)"""
    score = 0.0

    # 长度接近 (0-0.3)
    len_diff = abs(pa["length"] - pb["length"])
    if len_diff == 0:
        score += 0.3
    elif len_diff == 1:
        score += 0.2
    elif len_diff <= 2:
        score += 0.1

    # 深度接近 (0-0.2)
    dep_diff = abs(pa["depth"] - pb["depth"])
    if dep_diff <= 1:
        score += 0.2
    elif dep_diff <= 2:
        score += 0.1

    # 终点类型重叠 (0-0.3)
    shared_types = pa["end_types"] & pb["end_types"]
    if shared_types:
        score += 0.3 * len(shared_types) / max(len(pa["end_types"] | pb["end_types"]), 1)

    # 跨域加分 (0-0.2)
    domain_overlap = pa["domains"] & pb["domains"]
    if not domain_overlap:
        score += 0.2  # 完全跨域, 最有趣
    elif len(domain_overlap) <= 1:
        score += 0.1

    return min(score, 1.0)


def _extract_path_variables(chain: List[Dict]) -> List[str]:
    vars_set = []
    for step in chain:
        if "error" in step:
            continue
        cause = step.get("cause_variable", "")
        effect = step.get("effect_variable", "")
        if cause and cause not in vars_set:
            vars_set.append(cause)
        if effect and effect not in vars_set:
            vars_set.append(effect)
    return vars_set


def find_causal_analogies(max_chains: int = 15, min_similarity: float = 0.4) -> List[Dict]:
    """发现跨域因果链类比 (软匹配)"""
    from inference.counterfactual_chain import propagate
    from physics.laws import library, classify_variable

    # 选起点
    start_vars = []
    for law in library.list_all():
        for v in law.inputs:
            cat = classify_variable(v)
            if cat in ("fundamental", "geometric", "quantum"):
                start_vars.append(v)
    start_vars = list(set(start_vars))[:max_chains]

    # 传播 + 提取剖面
    profiles = []
    for var in start_vars:
        try:
            chain = propagate(var, "变化", max_depth=5)
            if chain and "error" not in chain[0] and len(chain) >= 2:
                profile = _chain_profile(chain)
                profiles.append({
                    "start_var": var,
                    "chain": chain,
                    "profile": profile,
                    "variables": _extract_path_variables(chain),
                    "length": profile["length"],
                })
        except Exception:
            pass

    # 所有配对计算相似度
    analogies = []
    for i, a in enumerate(profiles):
        for b in profiles[i+1:]:
            sim = _chain_similarity(a["profile"], b["profile"])

            # 必须有跨域元素
            domains_a = a["profile"]["domains"]
            domains_b = b["profile"]["domains"]
            cross = not domains_a.intersection(domains_b)
            partial_cross = len(domains_a & domains_b) <= 1

            if sim < min_similarity:
                continue
            if not cross and not partial_cross:
                continue

            insight = _generate_insight(a, b, sim)
            end_types_shared = a["profile"]["end_types"] & b["profile"]["end_types"]

            analogies.append({
                "chain_a_start": a["start_var"],
                "chain_b_start": b["start_var"],
                "domains_a": sorted(domains_a),
                "domains_b": sorted(domains_b),
                "length_a": a["length"],
                "length_b": b["length"],
                "similarity": round(sim, 2),
                "insight": insight,
                "variables_a": a["variables"][:6],
                "variables_b": b["variables"][:6],
                "end_types": sorted(end_types_shared) if end_types_shared else [],
            })

    analogies.sort(key=lambda x: x["similarity"], reverse=True)
    return analogies


def _generate_insight(a: Dict, b: Dict, sim: float) -> str:
    var_a, var_b = a["start_var"], b["start_var"]
    la, lb = a["length"], b["length"]
    da = "/".join(a["profile"]["domains"])
    db = "/".join(b["profile"]["domains"])

    if sim >= 0.7:
        return f"高度同构 ({sim:.0%}): {var_a}({da}) 和 {var_b}({db}) 的因果链结构几乎相同——可能对应不同域的同一种物理机制。"
    elif sim >= 0.5:
        if a["profile"]["end_types"] & b["profile"]["end_types"]:
            shared = a["profile"]["end_types"] & b["profile"]["end_types"]
            return f"部分同构 ({sim:.0%}): 两条链终点类型 {shared} 一致——不同域的路径汇聚于相同的终态类型。"
        return f"中等同构 ({sim:.0%}): {var_a} 和 {var_b} 的因果链长度/深度接近——值得进一步比对。"
    else:
        return f"弱同构 ({sim:.0%}): {var_a} 和 {var_b} 有相似的结构元素——可能有未被发现的桥接。"


def analogy_report() -> str:
    analogies = find_causal_analogies(min_similarity=0.4)

    lines = ["══════ 因果链类比 ══════"]
    lines.append(f"  发现 {len(analogies)} 条跨域结构类比")
    lines.append("")

    if not analogies:
        lines.append("  降低阈值后仍未发现跨域同构链。")
        lines.append("  建议: 手动运行 chain <var> 探索特定路径, 或 speculate 生成新边。")
        return "\n".join(lines)

    for i, a in enumerate(analogies[:10]):
        sim_bar = "█" * int(a["similarity"] * 8) + "░" * (8 - int(a["similarity"] * 8))
        end_info = f" 终点类型: {', '.join(a.get('end_types', []))}" if a.get("end_types") else ""
        lines.append(f"  {i+1}. [{a['similarity']:.0%} {sim_bar}]")
        lines.append(f"     {a['chain_a_start']} ({', '.join(a['domains_a'][:3])}) {a['length_a']}步")
        lines.append(f"       ↕")
        lines.append(f"     {a['chain_b_start']} ({', '.join(a['domains_b'][:3])}) {a['length_b']}步")
        if end_info:
            lines.append(f"     {end_info}")
        lines.append(f"     {a['insight'][:120]}")
        lines.append("")

    lines.append(f"  总计: {len(analogies)} 条 (相似度 ≥ 0.4)")
    return "\n".join(lines)
