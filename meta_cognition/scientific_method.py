"""
科学方法流水线 — 从缺口到实验的全自动流转

gap → why → hypothesize → analogize → reason → experiment

这是诺特作为物理学家的完整工作流。
"""

from __future__ import annotations
from typing import Dict, List


def experiment_proposal(hypothesis: Dict) -> Dict:
    """
    给定一个假说，提出验证实验。
    
    目前是"思想实验"版本 — 基于因果图结构推断可观测后果。
    等数学推导层就绪后升级为定量实验设计。
    """
    var_a = hypothesis.get("var_a", "")
    var_b = hypothesis.get("var_b", "")
    confidence = hypothesis.get("confidence", 0)
    beauty = hypothesis.get("beauty", 0)
    
    proposals = []
    
    # 类型1: 如果两端在不同的物理域 — 跨域预测
    from physics.laws import library
    
    domains_a = set()
    domains_b = set()
    for law in library._laws:
        if var_a in law.inputs + law.outputs:
            domains_a.add(law.domain)
        if var_b in law.inputs + law.outputs:
            domains_b.add(law.domain)
    
    cross_domain = not domains_a.intersection(domains_b) if domains_a and domains_b else False
    
    if cross_domain:
        proposals.append({
            "type": "cross_domain_prediction",
            "description": (
                f"如果 {var_a} ↔ {var_b} 的桥接成立，"
                f"则在 {list(domains_a)[:2]} 域的实验中应观察到 {var_b} 的行为"
            ),
            "difficulty": "medium",
            "requires": f"{list(domains_b)[:2]} 域的测量设备",
        })
    
    # 类型2: 如果两边都有对称性 — 对称性检验
    from meta_cognition.aesthetics import symmetry_score
    sym_a = symmetry_score(var_a)
    sym_b = symmetry_score(var_b)
    
    if sym_a > 0.5 and sym_b > 0.5:
        proposals.append({
            "type": "symmetry_verification",
            "description": (
                f"两者都承载对称性 ({sym_a:.1f}/{sym_b:.1f})。"
                f"验证实验: 寻找 {var_a} 和 {var_b} 共享的守恒量或规范结构"
            ),
            "difficulty": "hard",
            "requires": "对称群分析 + 守恒律验证",
        })
    
    # 类型3: 思想实验 — 反事实推理
    proposals.append({
        "type": "thought_experiment",
        "description": (
            f"假设 {var_a} → {var_b} 的边存在。"
            f"想象改变 {var_a} —— 如果 {var_b} 随之改变, 边被验证; 如果不变, 边被证伪。"
        ),
        "difficulty": "easy",
        "requires": "因果图反事实传播 (已具备)",
    })
    
    return {
        "variable_pair": f"{var_a}↔{var_b}",
        "confidence": confidence,
        "beauty": beauty,
        "proposals": proposals,
        "best_proposal": proposals[0]["description"] if proposals else "暂无可行实验提案",
    }


def scientific_method_on_gap(gap_name: str = None) -> Dict:
    """
    完整科学方法流水线: 对一个缺口执行全流程。
    
    gap → why → hypothesize → analogize → reason → experiment
    """
    from meta_cognition.puzzle_engine import scan_gaps
    from meta_cognition.why_engine import trace_to_root, propose_why_hypothesis
    from meta_cognition.hypothesis_generator import generate_hypotheses
    from creative.causal_analogy import find_causal_analogies
    from inference.counterfactual_chain import propagate
    
    result = {
        "gap": None,
        "why": None,
        "hypothesis": None,
        "analogies": [],
        "reasoning": None,
        "experiment": None,
    }
    
    # ═══ 阶段 1: GAP — 找缺口 ═══
    gaps = scan_gaps()
    if not gaps:
        result["gap"] = "no_gaps"
        return result
    
    gap = gaps[0]
    if gap_name:
        for g in gaps:
            if gap_name.lower() in g["name"].lower():
                gap = g
                break
    
    result["gap"] = {
        "name": gap["name"],
        "stars": gap["stars"],
        "status": gap["status"],
        "direction": gap["direction"],
    }
    
    # ═══ 阶段 2: WHY — 追溯根源 ═══
    # 从缺口描述中提取关键变量
    gap_text = gap["status"] + " " + gap.get("direction", "")
    from physics.laws import library
    candidate_vars = []
    for law in library._laws:
        for v in law.inputs + law.outputs:
            if v in gap_text or any(w in v for w in gap_text.split()[:5]):
                candidate_vars.append(v)
    candidate_vars = list(set(candidate_vars))[:3]
    
    why_results = []
    for v in candidate_vars:
        tr = trace_to_root(v)
        why_results.append({
            "variable": v,
            "type": tr["type"],
            "gap": tr.get("gap", ""),
        })
    result["why"] = why_results
    
    # ═══ 阶段 3: HYPOTHESIZE — 提假说 ═══
    bridgeable = [w for w in why_results if w["type"] == "gap_bridgeable"]
    if bridgeable:
        hyp = propose_why_hypothesis(bridgeable[0]["variable"])
        if hyp:
            result["hypothesis"] = hyp
    
    if not result["hypothesis"]:
        # 回退: 用 hypothesis_generator 找候选
        hyps = generate_hypotheses(min_confidence=0.2)
        if hyps:
            h = hyps[0]
            result["hypothesis"] = {
                "var_a": h["var_a"], "var_b": h["var_b"],
                "confidence": h["confidence"],
                "beauty": h.get("beauty", 0),
                "reason": h["reason"],
            }
    
    # ═══ 阶段 4: ANALOGIZE — 找类比支撑 ═══
    if result["hypothesis"]:
        h = result["hypothesis"]
        va = h.get("var_a") or h.get("variable") or ""
        vb = h.get("var_b") or h.get("analogous_to") or ""
        analogies = find_causal_analogies(min_similarity=0.3, novelty_bias=False)
        for an in analogies:
            if an.get("quality") != "solid":
                continue
            if va in (an.get("chain_a_start"), an.get("chain_b_start")) or \
               vb in (an.get("chain_a_start"), an.get("chain_b_start")):
                result["analogies"].append({
                    "pair": f"{an['chain_a_start']}↔{an['chain_b_start']}",
                    "similarity": an["similarity"],
                    "insight": an.get("insight", "")[:100],
                })
    
    # ═══ 阶段 5: REASON — 因果推理 ═══
    if result["hypothesis"]:
        h = result["hypothesis"]
        va = h.get("var_a") or h.get("variable") or ""
        vb = h.get("var_b") or h.get("analogous_to") or ""
        chain = propagate(va, "变化", max_depth=5, max_tier=2)
        effects = [s["effect_variable"] for s in chain if "error" not in s][:5]
        result["reasoning"] = {
            "from": va,
            "downstream_effects": effects,
            "implication": f"如果 {va} 桥接到 {vb}, 则 {va} 的下游效应 {effects[:3]} 也会影响 {vb}",
        }
    
    # ═══ 阶段 6: EXPERIMENT — 实验提案 ═══
    if result["hypothesis"]:
        result["experiment"] = experiment_proposal(result["hypothesis"])
    
    return result


def scientific_report(gap_name: str = None) -> str:
    """科学方法完整报告"""
    r = scientific_method_on_gap(gap_name)
    
    if r["gap"] == "no_gaps":
        return "所有缺口已填补。"
    
    lines = ["══════ 科学方法: 完整流水线 ══════"]
    
    # Gap
    g = r["gap"]
    lines.append(f"\n🔍 缺口: {g['name']} ({g['stars']}★)")
    lines.append(f"   {g['status'][:100]}")
    
    # Why
    lines.append(f"\n❓ 为什么:")
    for w in r["why"][:3]:
        icon = {"theorem": "✓", "gap_bridgeable": "🔗", "gap_cliff": "🪨", "gap_tier_mismatch": "⚠"}.get(w["type"], "?")
        lines.append(f"   {icon} {w['variable']}: {w['type']}")
    
    # Hypothesis
    if r["hypothesis"]:
        h = r["hypothesis"]
        lines.append(f"\n💡 假说: {h.get('var_a','?')} ↔ {h.get('var_b','?')}")
        lines.append(f"   置信: {h.get('confidence',0):.0%} | 审美: {h.get('beauty',0):.1f}")
        lines.append(f"   {h.get('reason', h.get('hypothesis',''))[:120]}")
    
    # Analogies
    if r["analogies"]:
        lines.append(f"\n🔗 类比支撑 ({len(r['analogies'])}):")
        for a in r["analogies"][:3]:
            lines.append(f"   {a['pair']} ({a['similarity']:.0%})")
    
    # Reasoning
    if r["reasoning"]:
        lines.append(f"\n🧠 推理: {r['reasoning']['implication'][:120]}")
    
    # Experiment
    if r["experiment"]:
        lines.append(f"\n🧪 实验提案:")
        lines.append(f"   {r['experiment']['best_proposal'][:120]}")
    
    return "\n".join(lines)
