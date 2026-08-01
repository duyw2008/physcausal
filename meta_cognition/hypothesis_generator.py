"""
主动假说生成器 — 诺特的大脑皮层

不只是被动扫描缺口。主动在因果图中找:
  1. 结构相似但不连通的变量对 → 提案"可能缺一条边"
  2. 跨域但因果骨架相同的变量 → 提案"可能同一个机制"
  3. 单边桥: A→X and B→Y, A和B相似 → 提案 X↔Y

然后: 对每个候选假说 → forbidden检查 → tier评估 → 评分排序
"""

from __future__ import annotations
from typing import Dict, List, Optional


def generate_hypotheses(min_confidence: float = 0.3) -> List[Dict]:
    """
    三步生成:
      1. 找结构相似但不连通的变量对 (analogy引擎)
      2. 找因果等价类中的跨域对 (abstraction引擎)  
      3. 合并 → forbidden过滤 → 评分
    """
    from creative.causal_analogy import find_causal_analogies
    from emergence.hierarchical_abstraction import discover_abstractions
    from inference.counterfactual_chain import propagate, build_dependency_graph
    from physics.laws import library, classify_variable
    from meta_cognition.learning_memory import calibrate_confidence, should_skip, record_hypothesis
    from meta_cognition.aesthetics import aesthetics_score

    graph = build_dependency_graph()
    hypotheses = []

    # ═══ 源1: 类比引擎 — 相似但不连通 ═══
    analogies = find_causal_analogies(min_similarity=0.3, novelty_bias=False)
    
    for an in analogies:
        if an.get("quality") != "solid":
            continue
        
        a = an["chain_a_start"]
        b = an["chain_b_start"]
        
        # 检查: a和b在图中是否连通?
        if a not in graph or b not in graph:
            continue
        
        # a能到达b吗?
        chain_ab = propagate(a, "变化", max_depth=6, max_tier=2)
        reaches = any(s.get("effect_variable") == b for s in chain_ab if "error" not in s)
        
        if not reaches:
            # 不连通! 提案桥接
            sim = an["similarity"]
            conf = sim * 0.7  # 高相似度但不连通 → 值得桥接
            
            # forbidden检查
            blocked = False
            for law in library._laws:
                for fd_src, fd_dst in law.forbidden_directions:
                    if (fd_src in a or a in fd_src) and (fd_dst in b or b in fd_dst):
                        blocked = True
                        break
            if blocked:
                continue
            
            if conf >= min_confidence:
                # 增量学习校准
                calib_conf = calibrate_confidence(a, b, conf)
                if should_skip(a, b):
                    continue
                hypotheses.append({
                    "source": "analogy_gap",
                    "var_a": a, "var_b": b,
                    "similarity": sim,
                    "confidence": round(calib_conf, 2),
                    "beauty": aesthetics_score(a, b, an.get("variables_a",[]), an.get("variables_b",[]),
                                               an.get("length_a",0), an.get("length_b",0)),
                    "reason": f"结构同构({sim:.0%})但因果不连通 — 可能缺一条边",
                })

    # ═══ 源2: 抽象引擎 ═══
    abstractions = discover_abstractions(min_similarity=0.2)
    
    for ab in abstractions:
        vars_list = ab.get("micro_vars", [])
        if len(vars_list) < 2:
            continue
        
        a, b = vars_list[0], vars_list[1]
        
        # 必须跨域
        doms_a = set(ab.get("domains", {}).get("a", []))
        doms_b = set(ab.get("domains", {}).get("b", []))
        if doms_a == doms_b:
            continue
        
        # 检查连通性
        if a not in graph or b not in graph:
            continue
        
        chain_ab = propagate(a, "变化", max_depth=6, max_tier=2)
        reaches = any(s.get("effect_variable") == b for s in chain_ab if "error" not in s)
        
        if not reaches:
            conf = ab.get("total_score", 0) * 0.6
            if conf >= min_confidence:
                calib_conf = calibrate_confidence(a, b, conf)
                if should_skip(a, b):
                    continue
                effects = ab.get("shared_effects", [])
                hypotheses.append({
                    "source": "abstraction_gap",
                    "var_a": a, "var_b": b,
                    "similarity": ab.get("causal_sim", 0),
                    "confidence": round(calib_conf, 2),
                    "beauty": aesthetics_score(a, b, None, None, 0, 0),
                    "reason": f"因果等价但跨域不连通 (共享效应: {effects[:2]})",
                })

    # 去重 + 排序 (置信度主序，审美辅助)
    seen = set()
    unique = []
    for h in sorted(hypotheses, key=lambda x: -(x["confidence"] + x.get("beauty", 0) * 0.1)):
        key = tuple(sorted([h["var_a"], h["var_b"]]))
        if key not in seen:
            seen.add(key)
            unique.append(h)

    return unique[:15]


def hypothesis_report() -> str:
    """假说报告 — 供 agent 命令"""
    hyps = generate_hypotheses(min_confidence=0.2)
    
    lines = ["══════ 主动假说 ══════"]
    lines.append(f"  候选: {len(hyps)}")
    
    if not hyps:
        lines.append("  (因果图连通度较高，无可行的单步桥接候选)")
        return "\n".join(lines)
    
    lines.append("")
    for i, h in enumerate(hyps[:8]):
        src = "🔗" if h["source"] == "analogy_gap" else "🧩"
        lines.append(f"  {i+1}. [{h['confidence']:.0%}] {src} {h['var_a']} ↔ {h['var_b']}")
        lines.append(f"     {h['reason']}")
        lines.append("")
    
    return "\n".join(lines)
