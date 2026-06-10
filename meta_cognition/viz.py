# -*- coding: utf-8 -*-
"""
可视化仪表盘 — ASCII 因果图 + 类比 + 驱动面板
"""

from __future__ import annotations
from typing import Dict, List


def drive_dashboard() -> str:
    """Noether 的驱动状态面板"""
    try:
        from meta_cognition.autonomous import AutonomousAgent
        a = AutonomousAgent()
        s = a.internal
    except:
        return "  自主状态未初始化"

    lines = ["═══ Noether 驱动面板 ═══"]
    
    def bar(val, width=20, label=""):
        filled = int(val * width)
        return f"{'█' * filled}{'░' * (width - filled)} {val:.0%} {label}"

    lines.append(f"  curiosity   {bar(s.curiosity_level, label='好奇心')}")
    lines.append(f"  energy      {bar(s.energy, label='精力')}")
    lines.append(f"  coherence   {bar(s.coherence_drive, label='一致性')}")
    lines.append(f"  novelty     {bar(s.novelty_drive, label='新颖性')}")
    lines.append(f"  hunger      {bar(s.pattern_hunger, label='模式饥饿')}")
    lines.append(f"  frustration {bar(s.frustration, label='沮丧')}")
    lines.append(f"  thoughts: {s.thought_count}  discoveries: {s.total_discoveries}")
    
    # 品味
    taste = s.taste_profile
    domains = taste.get("fruitful_domains", {})
    if domains:
        top = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:3]
        lines.append(f"  taste: {', '.join(f'{d}({c})' for d,c in top)}")
    
    return "\n".join(lines)


def analogy_map(n: int = 6) -> str:
    """类比连接图"""
    try:
        from creative.causal_analogy import find_causal_analogies
        analogies = find_causal_analogies(max_chains=10, min_similarity=0.6)
    except:
        return "  类比引擎未初始化"

    lines = [f"═══ 类比连接图 ({len(analogies)} 条) ═══"]
    
    # 按相似度分组
    for a in analogies[:n]:
        sim_bar = "█" * int(a["similarity"] * 8) + "░" * (8 - int(a["similarity"] * 8))
        lines.append(f"  {a['chain_a_start']:<20s} ──[{sim_bar}]──▶ {a['chain_b_start']}")
        lines.append(f"  {'':20s} {a['similarity']:.0%}")

    return "\n".join(lines)


def chain_viz(var: str, max_depth: int = 4) -> str:
    """单变量因果链可视化"""
    from inference.counterfactual_chain import propagate
    chain = propagate(var, "变化", max_depth=max_depth)

    lines = [f"═══ {var} 因果链 ═══"]
    indent_map = {}
    for step in chain:
        if "error" in step:
            continue
        depth = step.get("depth", 0)
        cause = step.get("cause_variable", "?")
        effect = step.get("effect_variable", "?")
        law = step.get("law", "?")
        domain = step.get("domain", "?")
        indent = "  " * depth
        lines.append(f"{indent}{cause} → {effect} [{law}, {domain}]")

    return "\n".join(lines)


def viz_report() -> str:
    """综合可视化报告"""
    parts = [drive_dashboard(), "", analogy_map(6)]
    return "\n".join(parts)
