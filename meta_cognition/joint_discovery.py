"""
联合发现引擎 — 三引擎闭环: 拼图→抽象→类比→拼图

流程:
  1. 拼图扫描缺口 → 选最高优先级
  2. 在缺口附近的因果空间中，抽象引擎找等价类
  3. 对最有希望的等价类，类比引擎验证跨域结构同构
  4. 如果有 solid 类比支撑 → 提案桥接 → 更新拼图

像物理学家一样工作: 发现问题 → 联想已知 → 验证猜想 → 更新认知
"""

from __future__ import annotations
from typing import Dict, List, Optional


def joint_discovery_cycle(verbose: bool = True) -> Dict:
    """
    一次完整的联合发现周期。
    
    Returns:
        {
            "gap": str,           # 处理的缺口
            "abstract_findings": [],  # 抽象引擎发现
            "analogy_validation": [], # 类比验证结果
            "proposal": str,       # 最终提案
            "confidence": float,   # 综合置信度
            "pipeline": str,       # 流水线描述
        }
    """
    from meta_cognition.puzzle_engine import scan_gaps, propose_bridge
    from emergence.hierarchical_abstraction import discover_abstractions
    from creative.causal_analogy import find_causal_analogies
    from physics.laws import classify_variable

    # ═══ 阶段 1: 拼图 — 找缺口 ═══
    gaps = scan_gaps()
    if not gaps:
        return {"gap": None, "abstract_findings": [], "analogy_validation": [],
                "proposal": "no gaps found", "confidence": 0, "pipeline": "puzzle:0gaps"}

    top_gap = gaps[0]
    gap_name = top_gap["name"]
    
    if verbose:
        print(f"[puzzle] 缺口: {gap_name} ({top_gap['stars']}★)")

    # ═══ 阶段 2: 抽象 — 在缺口区找等价类 ═══
    # 确定缺口涉及的关键域
    gap_keywords = {
        "电磁": ["electromagnetism", "charge", "current", "electric", "magnetic", "gauge", "em"],
        "KK": ["unification", "compact", "higher_d", "gauge_field", "extra"],
        "量子引力": ["quantum", "general_relativity", "spacetime", "entangled", "wormhole"],
        "时间": ["thermodynamics", "relaxation", "entropy", "time"],
    }
    
    related_domains = ["quantum", "thermodynamics", "general_relativity", "unification"]
    for kw, doms in gap_keywords.items():
        if kw in gap_name:
            related_domains = doms
            break

    # 运行抽象引擎
    abstractions = discover_abstractions(min_similarity=0.2)
    
    # 筛选: 只看与缺口域相关的等价类
    relevant_abs = []
    for ab in abstractions:
        abs_domains = set(ab.get("domains", {}).get("a", [])) | set(ab.get("domains", {}).get("b", []))
        domain_match = any(
            any(rd in str(d).lower() for rd in related_domains)
            for d in abs_domains
        )
        if domain_match and ab.get("total_score", 0) >= 0.3:
            relevant_abs.append(ab)

    if verbose:
        print(f"[abstract] 相关等价类: {len(relevant_abs)}/{len(abstractions)}")

    # ═══ 阶段 3: 类比 — 验证最可能的桥接 ═══
    analogy_support = []
    top_candidates = sorted(relevant_abs, key=lambda x: -x.get("total_score", 0))[:5]

    # 取等价类中的变量，跑类比引擎
    candidate_vars = set()
    for ab in top_candidates:
        candidate_vars.update(ab.get("micro_vars", []))

    # 对每对候选变量，检查是否已有跨域类比支持
    analogies = find_causal_analogies(min_similarity=0.3, novelty_bias=False)

    for ab in top_candidates[:3]:
        vars_a = ab.get("micro_vars", [])
        for an in analogies:
            chain_a = an.get("chain_a_start", "")
            chain_b = an.get("chain_b_start", "")
            if (chain_a in vars_a or chain_b in vars_a) and an.get("quality") == "solid":
                analogy_support.append({
                    "equivalence": f"{vars_a[0]}↔{vars_a[1]}" if len(vars_a) >= 2 else str(vars_a),
                    "analogy": f"{chain_a}↔{chain_b}",
                    "similarity": an.get("similarity", 0),
                    "quality": an.get("quality", "?"),
                })

    if verbose and analogy_support:
        print(f"[analogy] 验证支持: {len(analogy_support)} 条")
        for s in analogy_support[:2]:
            print(f"  {s['analogy']} ({s['similarity']:.0%}, {s['quality']})")

    # ═══ 阶段 4: 综合提案 ═══
    proposal = ""
    confidence = 0.0

    if analogy_support:
        # 有类比支撑 → 提案具体桥接
        best_abs = top_candidates[0] if top_candidates else None
        if best_abs:
            vars_list = best_abs.get("micro_vars", [])
            effects = best_abs.get("shared_effects", [])
            proposal = f"桥接 {vars_list[0]}↔{vars_list[1]} (共享效应: {effects[:2]})"
            # 置信度 = 抽象得分 × (1 + 类比支持数/3)
            abs_score = best_abs.get("total_score", 0)
            support_bonus = min(len(analogy_support) / 3, 1.0)
            confidence = round(abs_score * (1 + support_bonus * 0.5), 2)
            confidence = min(confidence, 1.0)
    elif relevant_abs:
        # 有等价类但无类比支撑 → 较弱提案
        best_abs = top_candidates[0]
        vars_list = best_abs.get("micro_vars", [])
        proposal = f"探索 {vars_list[0]}↔{vars_list[1]} 的可能桥接 (无 solid 类比验证)"
        confidence = round(best_abs.get("total_score", 0) * 0.3, 2)
    else:
        proposal = f"缺口 {gap_name}: 附近无可行的因果等价类"
        confidence = 0.1

    if verbose:
        print(f"[proposal] {proposal} (置信度: {confidence:.0%})")

    return {
        "gap": gap_name,
        "gap_priority": top_gap.get("stars", 1),
        "abstract_findings": len(relevant_abs),
        "abstract_top": [{"name": a["name"], "score": a["total_score"], "vars": a["micro_vars"]}
                         for a in top_candidates[:3]],
        "analogy_validation": analogy_support,
        "proposal": proposal,
        "confidence": confidence,
        "pipeline": f"puzzle→abstract({len(relevant_abs)})→analogy({len(analogy_support)})→proposal",
        "interesting": confidence >= 0.3,
    }


def joint_report() -> str:
    """联合发现报告 (供 agent 命令)"""
    result = joint_discovery_cycle(verbose=False)

    lines = ["══════ 联合发现 ══════"]
    lines.append(f"  缺口: {result['gap']} ({result['gap_priority']}★)")
    lines.append(f"  抽象: {result['abstract_findings']} 相关等价类")
    lines.append(f"  类比: {len(result['analogy_validation'])} 条验证")
    lines.append(f"  流水线: {result['pipeline']}")
    lines.append(f"  置信度: {result['confidence']:.0%}")
    lines.append("")
    lines.append(f"  提案: {result['proposal']}")

    if result.get("abstract_top"):
        lines.append("")
        lines.append("  等价类候选:")
        for a in result["abstract_top"]:
            lines.append(f"    {a['name']} [{a['score']:.2f}] {a['vars']}")

    return "\n".join(lines)
