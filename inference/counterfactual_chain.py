"""
反事实链传播 — 沿因果图正向传播假设变化

给定一个初始条件的改变 ("如果地球质量减半"),
沿 causal_direction 逐条定律正向传播影响,
每一步都由物理定律验证, 最终输出可检验的预测。

核心:
  1. 构建定律依赖图 (变量→定律→因果方向)
  2. 从初始条件开始正向传播
  3. 每步: 查定律→应用公式→检查 forbidden→记录链
  4. 最大深度限制, 避免环路
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np


def build_dependency_graph():
    """
    从定律库构建因果依赖图。

    Returns:
        {
            "mass": {
                "as_input": [("Newton II", "acceleration"), ("Gravity", "force_gravity"), ...],
                "as_output": [("Newton II", "force"), ...]
            },
            ...
        }
    """
    from physics.laws import library

    graph = {}
    for law in library.list_all():
        for src, dst in law.causal_direction:
            # src → dst: src causes dst
            if src not in graph:
                graph[src] = {"as_input": [], "as_output": []}
            if dst not in graph:
                graph[dst] = {"as_input": [], "as_output": []}

            graph[src]["as_input"].append((law.name, dst, law.domain))
            graph[dst]["as_output"].append((law.name, src, law.domain))

    return graph


def propagate(variable: str, change: str, max_depth: int = 5,
              max_tier: int = 4) -> List[Dict]:
    """
    沿因果图正向传播一个假设变化。

    Args:
        variable: 改变的变量名
        change: 改变描述
        max_depth: 最大传播深度
        max_tier: 只使用 confidence_tier <= max_tier 的定律 (默认 4 = 全部)

    Returns:
        [{depth, variable, law, effect, new_variable, chain_path, confidence_tier}, ...]
    """
    from physics.laws import library

    graph = build_dependency_graph()
    if variable not in graph:
        for v in graph:
            if variable in v or v in variable:
                variable = v
                break
        else:
            return [{"depth": 0, "variable": variable, "error": "variable not in law library"}]

    node = graph[variable]
    if not node["as_input"]:
        return [{"depth": 0, "variable": variable, "error": "no downstream effects"}]

    chain = []
    visited = set()
    queue = [(variable, change, 0, [f"{variable}{change}"])]

    while queue and len(chain) < max_depth * 3:
        var, chg, depth, path = queue.pop(0)
        if var in visited or depth >= max_depth:
            continue
        visited.add(var)

        node = graph.get(var, {"as_input": [], "as_output": []})
        for law_name, effect_var, domain in node["as_input"]:
            law = None
            for l in library.list_all():
                if l.name == law_name:
                    law = l
                    break
            if not law:
                continue

            # ── 置信层级过滤 ──
            if getattr(law, 'confidence_tier', 1) > max_tier:
                continue

            blocked = False
            for fd_src, fd_dst in law.forbidden_directions:
                if (fd_src in var or var in fd_src) and (fd_dst in effect_var or effect_var in fd_dst):
                    blocked = True
                    break
            if blocked:
                continue

            step = {
                "depth": depth + 1,
                "variable": var,
                "change": chg,
                "law": law_name,
                "domain": domain,
                "effect_variable": effect_var,
                "effect_description": f"{var}{chg} → {effect_var} 变化 ({law_name}, {domain})",
                "chain_path": path + [f"{var}→{effect_var}"],
                "confidence_tier": getattr(law, 'confidence_tier', 1),
            }
            chain.append(step)
            queue.append((effect_var, "变化", depth + 1, step["chain_path"]))

    return chain if chain else [{"depth": 0, "variable": variable, "error": "propagation yielded no results"}]


def format_chain(chain: List[Dict]) -> str:
    """人类可读的反事实链"""
    if not chain or "error" in chain[0]:
        return f"Cannot propagate: {chain[0].get('error', 'unknown')}"

    lines = ["=== Counterfactual Chain Propagation ==="]
    lines.append(f"Initial: {chain[0].get('variable', '?')} {chain[0].get('change', '?')}")
    lines.append("")

    for step in chain:
        indent = "  " * step["depth"]
        tier = step.get("confidence_tier", 1)
        tier_mark = {0: "◎", 1: "●", 2: "○", 3: "◇", 4: "?"}.get(tier, "●")
        lines.append(f"{indent}└─ [{step['domain']}] {tier_mark} {step['law']}")
        lines.append(f"{indent}   {step['effect_description']}")

    lines.append("")
    lines.append(f"Total propagation steps: {len(chain)}")
    return "\n".join(lines)


def propagate_tiered(variable: str, change: str = "变化",
                     max_depth: int = 5) -> Dict:
    """
    多层置信传播 — 分别在公理+共识 (tier 0-1) 和全层级 (tier 0-4) 上运行 chain,
    比较结果。

    如果两条链在某个变量上汇聚, 说明探索性假说与已知物理一致 — 弱验证信号。

    Returns:
        {
            "axiom_chain": [...],       # tier 0-1 的链
            "full_chain": [...],        # tier 0-4 的链 (含探索)
            "convergences": [...],      # 两条链汇聚的变量
            "validation_score": float,  # 0-1, 越高越可信
        }
    """
    axiom_chain = propagate(variable, change, max_depth, max_tier=1)
    full_chain = propagate(variable, change, max_depth, max_tier=4)

    # 收集两条链中各深度出现的变量
    axiom_vars: Dict[str, int] = {}   # variable → min_depth
    for s in axiom_chain:
        if "error" in s:
            continue
        v = s.get("effect_variable", "")
        d = s.get("depth", 0)
        if v and (v not in axiom_vars or d < axiom_vars[v]):
            axiom_vars[v] = d

    full_vars: Dict[str, int] = {}
    for s in full_chain:
        if "error" in s:
            continue
        v = s.get("effect_variable", "")
        d = s.get("depth", 0)
        if v and (v not in full_vars or d < full_vars[v]):
            full_vars[v] = d

    # 找汇聚: 两条链都到达的变量
    convergences = []
    for var in sorted(set(axiom_vars) & set(full_vars)):
        # 只在探索链更深时才算汇聚 (公理链自己就能到的变量不算)
        if full_vars[var] > axiom_vars.get(var, 999):
            continue
        convergences.append({
            "variable": var,
            "axiom_depth": axiom_vars[var],
            "full_depth": full_vars[var],
        })

    # 弱验证分数: 汇聚变量越多, 探索链与公理链越一致
    total_full_vars = len(full_vars)
    score = len(convergences) / max(total_full_vars, 1) if total_full_vars > 0 else 0

    return {
        "axiom_chain": axiom_chain,
        "full_chain": full_chain,
        "convergences": convergences,
        "validation_score": round(score, 2),
    }


def format_tiered_comparison(result: Dict) -> str:
    """人类可读的多层对比报告"""
    conv = result.get("convergences", [])
    score = result.get("validation_score", 0)

    lines = ["=== 多层置信传播对比 ==="]
    lines.append(f"公理链 (tier 0-1): {len(result.get('axiom_chain', []))} steps")
    lines.append(f"全层级链 (tier 0-4): {len(result.get('full_chain', []))} steps")

    if conv:
        lines.append(f"\n汇聚节点 ({len(conv)}):")
        for c in conv:
            lines.append(f"  ✓ {c['variable']} — 公理链深度 {c['axiom_depth']}, 全链深度 {c['full_depth']}")
        if score >= 0.5:
            lines.append(f"\n弱验证通过 (score={score}): 探索性定律与公理链高度一致")
        elif score >= 0.2:
            lines.append(f"\n弱验证部分通过 (score={score}): 探索性定律与公理链部分一致")
        else:
            lines.append(f"\n弱验证不足 (score={score}): 探索性定律与公理链分歧较大")
    else:
        lines.append("\n无汇聚 — 探索性链未与公理链交汇")

    return "\n".join(lines)
