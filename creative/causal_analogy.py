"""
因果链类比发现 — 跨域结构联想 (v2: 软匹配)

用结构相似度代替精确签名匹配,
让物理学家可以自动发现"耗散 ≈ 退相干"这类深层类比。
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Set
from collections import defaultdict


def _chain_profile(chain: List[Dict]) -> Dict:
    """提取因果链的结构剖面，含置信层级分析"""
    domains = []
    end_types = set()
    depth = 0
    tiers = []

    for step in chain:
        if "error" in step:
            continue
        dom = step.get("domain", "?")[:3]
        domains.append(dom)
        eff = step.get("effect_variable", "")
        d = step.get("depth", 0)
        if d > depth:
            depth = d
        tier = step.get("confidence_tier", 1)
        tiers.append(tier)

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

    # ── 质量分析 ──
    max_tier = max(tiers) if tiers else 1
    min_tier = min(tiers) if tiers else 1
    speculative_count = sum(1 for t in tiers if t >= 3)
    root_tier = tiers[0] if tiers else 1

    if max_tier <= 2:
        quality = "solid"
    elif root_tier >= 3 and all(t <= 2 for t in tiers[1:]):
        quality = "speculative_root"
    else:
        quality = "speculative_path"

    return {
        "length": length,
        "depth": depth,
        "domains": domain_set,
        "end_types": end_types,
        "domain_seq": "/".join(domains),
        "max_tier": max_tier,
        "min_tier": min_tier,
        "root_tier": root_tier,
        "speculative_count": speculative_count,
        "quality": quality,
    }


def _semantic_similarity(var_a: str, var_b: str) -> float:
    """物理语义相似度 — 不看图拓扑，看变量本身的物理属性"""
    from physics.laws import classify_variable

    cat_a = classify_variable(var_a)
    cat_b = classify_variable(var_b)
    score = 0.0

    # 同类型 +0.3 (fundamental↔fundamental, quantum↔quantum)
    if cat_a == cat_b:
        score += 0.3
    # 基础↔几何 +0.2 (都是"深层"变量)
    elif {cat_a, cat_b} in ({'fundamental', 'geometric'}, {'quantum', 'geometric'}):
        score += 0.2
    # 派生↔基础 +0.1 (一个深层一个浅层)
    elif 'derived' in (cat_a, cat_b):
        score += 0.1

    # 守恒量加分 (charge, momentum, energy — Noether 产物)
    conserved = {'charge', 'momentum', 'energy', 'mass'}
    if var_a in conserved and var_b in conserved:
        score += 0.2
    elif var_a in conserved or var_b in conserved:
        score += 0.1

    # 几何变量加分 (spacetime_curvature, geodesic_path, gauge_field — Wheeler系)
    geometric = {'spacetime_curvature', 'geodesic_path', 'gauge_field', '4d_metric',
                 'higher_d_metric', 'compact_dimension', 'schwarzschild_radius'}
    if var_a in geometric and var_b in geometric:
        score += 0.2

    return min(score, 0.7)


def _chain_similarity(pa: Dict, pb: Dict, semantic_weight: float = 0.3) -> float:
    """计算两条因果链的相似度: 结构(70%) + 语义(30%)"""
    try:
        from creative.graph_features import analogy_similarity
        struct_sim = analogy_similarity(pa.get("start_var", ""), pb.get("start_var", ""))
    except Exception:
        struct_sim = 0.0
        len_diff = abs(pa["length"] - pb["length"])
        if len_diff == 0:
            struct_sim += 0.3
        elif len_diff <= 1:
            struct_sim += 0.2
        shared_types = pa["end_types"] & pb["end_types"]
        if shared_types:
            struct_sim += 0.3 * len(shared_types) / max(len(pa["end_types"] | pb["end_types"]), 1)
        domain_overlap = pa["domains"] & pb["domains"]
        if not domain_overlap:
            struct_sim += 0.2
        struct_sim = min(struct_sim, 1.0)

    # 语义分数
    sem_sim = _semantic_similarity(
        pa.get("start_var", ""),
        pb.get("start_var", "")
    )

    # 组合: 结构主导，语义微调
    combined = struct_sim * (1 - semantic_weight) + sem_sim * semantic_weight
    return min(combined, 1.0)


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


def find_causal_analogies(max_chains: int = 15, min_similarity: float = 0.4,
                         novelty_bias: bool = True) -> List[Dict]:
    """发现跨域因果链类比 (软匹配 + 新颖性偏置)"""
    from inference.counterfactual_chain import propagate
    from physics.laws import library, classify_variable
    import random, json, os

    # 选起点 — 随机化避免每次都选同一批
    all_start_vars = []
    for law in library.list_all():
        for v in law.inputs:
            cat = classify_variable(v)
            if cat in ("fundamental", "geometric", "quantum"):
                all_start_vars.append(v)
    all_start_vars = list(set(all_start_vars))

    # 新颖性: 读取最近发现的类比对, deprioritize
    recent_pairs = set()
    novelty_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "recent_analogies.json"
    )
    if novelty_bias:
        try:
            with open(novelty_path) as f:
                recent = json.load(f)
            for r in recent:
                recent_pairs.add(tuple(sorted([r['chain_a_start'], r['chain_b_start']])))
        except Exception:
            pass

    # 随机打乱起点
    random.shuffle(all_start_vars)
    start_vars = all_start_vars[:max_chains]

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
                "quality": _combine_quality(a["profile"]["quality"], b["profile"]["quality"]),
                "quality_a": a["profile"]["quality"],
                "quality_b": b["profile"]["quality"],
                "max_tier_a": a["profile"]["max_tier"],
                "max_tier_b": b["profile"]["max_tier"],
                "insight": insight,
                "variables_a": a["variables"][:6],
                "variables_b": b["variables"][:6],
                "end_types": sorted(end_types_shared) if end_types_shared else [],
            })

    # 新颖性: 对最近见过的对降权
    if novelty_bias and recent_pairs:
        for an in analogies:
            pair = tuple(sorted([an["chain_a_start"], an["chain_b_start"]]))
            if pair in recent_pairs:
                an["similarity"] = round(an["similarity"] * 0.5, 2)  # 降权50%

    analogies.sort(key=lambda x: x["similarity"], reverse=True)

    # 保存最近发现 (最多30条)
    if novelty_bias:
        top_for_memory = analogies[:15]
        try:
            os.makedirs(os.path.dirname(novelty_path), exist_ok=True)
            with open(novelty_path, "w") as f:
                json.dump([{
                    "chain_a_start": a["chain_a_start"],
                    "chain_b_start": a["chain_b_start"],
                    "similarity": a["similarity"],
                } for a in top_for_memory], f)
        except Exception:
            pass

    return analogies


def _combine_quality(qa: str, qb: str) -> str:
    """合并两条链的质量标签"""
    if qa == "solid" and qb == "solid":
        return "solid"
    elif qa == "solid" or qb == "solid":
        return "speculative_mixed"
    return "speculative"


def _generate_insight(a: Dict, b: Dict, sim: float) -> str:
    var_a, var_b = a["start_var"], b["start_var"]
    la, lb = a["length"], b["length"]
    da = "/".join(a["profile"]["domains"])
    db = "/".join(b["profile"]["domains"])
    qa = a["profile"]["quality"]
    qb = b["profile"]["quality"]

    # ── 质量后缀 ──
    qual_suffix = ""
    if qa != "solid" or qb != "solid":
        parts = []
        if qa == "speculative_root":
            parts.append(f"{var_a} 根在 tier≥3")
        elif qa == "speculative_path":
            parts.append(f"{var_a} 路径含 tier≥3")
        if qb == "speculative_root":
            parts.append(f"{var_b} 根在 tier≥3")
        elif qb == "speculative_path":
            parts.append(f"{var_b} 路径含 tier≥3")
        if parts:
            qual_suffix = f" ⚠ {'; '.join(parts)}"

    if sim >= 0.7:
        return f"高度同构 ({sim:.0%}): {var_a}({da}) 和 {var_b}({db}) 的因果链结构几乎相同——可能对应不同域的同一种物理机制。{qual_suffix}"
    elif sim >= 0.5:
        if a["profile"]["end_types"] & b["profile"]["end_types"]:
            shared = a["profile"]["end_types"] & b["profile"]["end_types"]
            return f"部分同构 ({sim:.0%}): 两条链终点类型 {shared} 一致——不同域的路径汇聚于相同的终态类型。{qual_suffix}"
        return f"中等同构 ({sim:.0%}): {var_a} 和 {var_b} 的因果链长度/深度接近——值得进一步比对。{qual_suffix}"
    else:
        return f"弱同构 ({sim:.0%}): {var_a} 和 {var_b} 有相似的结构元素——可能有未被发现的桥接。{qual_suffix}"


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
        quality_icon = {"solid": "●", "speculative_mixed": "◇", "speculative": "⚠"}.get(a.get("quality", ""), "")
        lines.append(f"  {i+1}. [{a['similarity']:.0%} {sim_bar}] {quality_icon} {a.get('quality','?')}")
        lines.append(f"     {a['chain_a_start']} ({', '.join(a['domains_a'][:3])}) {a['length_a']}步 [tier≤{a.get('max_tier_a',1)}]")
        lines.append(f"       ↕")
        lines.append(f"     {a['chain_b_start']} ({', '.join(a['domains_b'][:3])}) {a['length_b']}步 [tier≤{a.get('max_tier_b',1)}]")
        if end_info:
            lines.append(f"     {end_info}")
        lines.append(f"     {a['insight'][:120]}")
        lines.append("")

    lines.append(f"  总计: {len(analogies)} 条 (相似度 ≥ 0.4)")
    return "\n".join(lines)
