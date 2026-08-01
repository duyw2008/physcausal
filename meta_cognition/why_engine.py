"""
为什么引擎 — 诺特的科学追问能力

流程:
  1. 给定一个发现 (变量/汇聚模式) → 追溯是否能从 δS=0 推导
  2. 能 → 这是定理，给出推导路径
  3. 不能 → 定位阻断边，提出最小假说桥接
  4. 假说 → 检查自洽性 (forbidden, tier, 与已有定律冲突)
  5. 通过 → 注册为候选理论，标记"待数学推导/实验验证"

这就是"问为什么"的结构化实现。
"""

from __future__ import annotations
from typing import Dict, List, Optional


def trace_to_root(variable: str, max_depth: int = 10) -> Dict:
    """
    追溯一个变量是否能从 δS=0 (action) 推导。
    
    Returns:
        {"reachable": bool, "path": [...], "depth": int, "gap": str or None}
    """
    from inference.counterfactual_chain import propagate, build_dependency_graph
    from physics.laws import library

    ROOT = "action"
    graph = build_dependency_graph()

    if variable not in graph:
        return {"reachable": False, "path": [], "depth": 0, 
                "gap": f"变量 '{variable}' 不在因果图中", "explanation": None}

    # 正向: action → variable
    chain = propagate(ROOT, "极值化", max_depth=max_depth, max_tier=2)
    
    path_steps = []
    reached = False
    for s in chain:
        if "error" in s:
            continue
        path_steps.append(s)
        if s["effect_variable"] == variable:
            reached = True
            break

    if reached:
        # 成功 — 这是定理
        path = [ROOT] + [s["effect_variable"] for s in path_steps 
                         if s["effect_variable"] not in [ROOT] and s["depth"] <= max_depth]
        depth = len([s for s in path_steps if s["effect_variable"] == variable])
        if depth == 0:
            depth = path_steps[-1]["depth"] if path_steps else 0
        
        return {
            "reachable": True,
            "path": path,
            "depth": path_steps[-1]["depth"] if path_steps else 0,
            "gap": None,
            "explanation": f"δS=0 → ... → {variable} ({len(path)} 步, depth={path_steps[-1]['depth'] if path_steps else '?'})",
            "type": "theorem",
        }

    # 不可达 — 需要假说
    # 找最近的可达变量
    reached_vars = set()
    for s in chain:
        if "error" not in s:
            reached_vars.add(s["effect_variable"])
    reached_vars.add(ROOT)

    # 找 variable 在图中最近的入边邻居
    node = graph.get(variable, {"as_output": []})
    upstream = [(cause, law, domain) for law, cause, domain in node["as_output"]]
    
    # 检查: variable 的哪个上游已经可达?
    bridgeable = []
    for cause, law, domain in upstream:
        if cause in reached_vars:
            bridgeable.append({
                "from": cause,
                "to": variable,
                "via_law": law,
                "domain": domain,
                "status": "already_connected",
            })

    # 如果已经连了但 propagate 没探测到 → 可能是 tier 过滤问题
    if bridgeable:
        return {
            "reachable": False,
            "path": [ROOT] + list(reached_vars)[:5],
            "depth": max_depth,
            "gap": f"边 {bridgeable[0]['from']}→{variable} 存在但 propagate 未遍历",
            "explanation": None,
            "type": "gap_tier_mismatch",
        }

    # 真正不可达 — 需要假说。但区分两种:
    #   gap_bridgeable: 缺东西 — 类比提示存在，可以尝试桥接
    #   gap_cliff: 悬崖 — 连类比都找不到，物理学还没答案

    from creative.causal_analogy import find_causal_analogies
    analogies = find_causal_analogies(min_similarity=0.3, novelty_bias=False)
    
    best_analogy = None
    for an in analogies:
        if an.get("quality") != "solid":
            continue
        if variable in (an.get("chain_a_start"), an.get("chain_b_start")):
            other = an["chain_a_start"] if an["chain_b_start"] == variable else an["chain_b_start"]
            if other in reached_vars:
                if best_analogy is None or an["similarity"] > best_analogy["similarity"]:
                    best_analogy = an
                    best_analogy["analogous_reachable"] = other

    if best_analogy:
        gap_type = "gap_bridgeable"
        gap_msg = (f"从 δS=0 到 {variable} 的路径缺失。"
                   f"但 {variable} 与 {best_analogy['analogous_reachable']} 结构同构 ({best_analogy['similarity']:.0%})"
                   f"— {best_analogy['analogous_reachable']} 可达，暗示 {variable} 可能有类似路径")
    else:
        gap_type = "gap_cliff"
        gap_msg = (f"从 δS=0 到 {variable} 的路径缺失。"
                   f"且找不到任何结构相似的已可达变量。"
                   f"此处可能是物理学的前沿悬崖——尚无理论给出答案。")

    return {
        "reachable": False,
        "path": list(reached_vars)[:5],
        "depth": max_depth,
        "gap": gap_msg,
        "explanation": None,
        "type": gap_type,
        "analogy_hint": best_analogy,
    }


def why(variable: str) -> str:
    """问为什么 — 对一个变量追溯其物理根源"""
    result = trace_to_root(variable)
    
    lines = [f"══════ 为什么: {variable} ══════"]
    
    if result["type"] == "theorem":
        lines.append(f"  这是定理。可从 δS=0 推导:")
        path = result["path"]
        lines.append(f"  action → {' → '.join(path[1:6])}")
        if len(path) > 6:
            lines.append(f"  ... → {path[-1]} (共 {len(path)-1} 步)")
        lines.append(f"  深度: {result['depth']}")
    
    elif result["type"] == "gap_tier_mismatch":
        lines.append(f"  ⚠ 边存在但 propagate 未遍历 (可能 tier 过滤)")
        lines.append(f"  缺口: {result['gap']}")
    
    elif result["type"] == "gap_bridgeable":
        lines.append(f"  🔗 缺东西 — 可以尝试桥接")
        lines.append(f"  {result['gap']}")
        hint = result.get("analogy_hint")
        if hint:
            lines.append(f"  {variable} 与 {hint['analogous_reachable']} 结构同构 ({hint['similarity']:.0%})")
    
    elif result["type"] == "gap_cliff":
        lines.append(f"  🪨 悬崖 — 物理学尚无答案")
        lines.append(f"  {result['gap']}")
    
    return "\n".join(lines)


def propose_why_hypothesis(variable: str) -> Optional[Dict]:
    """
    对不可达变量，提出最小假说桥接。
    """
    result = trace_to_root(variable)
    if result.get("type") not in ("gap_bridgeable",):
        return None

    from meta_cognition.learning_memory import should_skip, calibrate_confidence
    from meta_cognition.aesthetics import aesthetics_score
    from physics.laws import library

    hint = result.get("analogy_hint")
    if not hint:
        return None

    reachable_var = hint["analogous_reachable"]
    
    if should_skip(variable, reachable_var):
        return None

    # 假说: variable 应该像 reachable_var 一样连接到 action
    conf = hint["similarity"] * 0.6
    conf = calibrate_confidence(variable, reachable_var, conf)
    beauty = aesthetics_score(variable, reachable_var)

    return {
        "variable": variable,
        "analogous_to": reachable_var,
        "similarity": hint["similarity"],
        "confidence": round(conf, 2),
        "beauty": beauty,
        "hypothesis": f"{variable} 可能与 {reachable_var} 共享因果骨架 — 建议在两者间搜索桥接路径",
        "action": f"在因果图中搜索 {variable}←{reachable_var} 的桥接变量",
    }
