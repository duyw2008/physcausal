"""
物理学家发言系统 — 让 agent 有自己的声音

不是被动回答命令, 而是主动提出见解、建议、观察。

数据源:
  - 最近类比发现 (causal_analogy)
  - 自主状态 (hunger/frustration/curiosity)
  - 聚焦方向 (research_directions)
  - 交叉验证汇总 (cv_summary)

输出: 自然语言洞察 + 建议
"""

from __future__ import annotations
from typing import Dict, List, Optional
import random


def _recent_analogies(n: int = 3) -> List[Dict]:
    """获取最近的类比发现"""
    try:
        from creative.causal_analogy import find_causal_analogies
        return find_causal_analogies(max_chains=12, min_similarity=0.5)[:n]
    except Exception:
        return []


def _state_snapshot() -> Dict:
    """获取当前自主状态"""
    try:
        from meta_cognition.autonomous import AutonomousAgent
        a = AutonomousAgent()
        s = a.internal
        return {
            "energy": s.energy,
            "curiosity": s.curiosity_level,
            "hunger": s.pattern_hunger,
            "frustration": s.frustration,
            "thoughts": s.thought_count,
            "discoveries": s.total_discoveries,
        }
    except Exception:
        return {"energy": 1.0, "hunger": 0, "frustration": 0, "curiosity": 0.5,
                "thoughts": 0, "discoveries": 0}


def _cv_summary() -> Dict:
    """交叉验证汇总"""
    try:
        from data_paths import load_cv_summary
        reports = load_cv_summary()
        passed = sum(1 for r in reports if r.get("convergence_preserved") is True)
        broken = sum(1 for r in reports if r.get("convergence_preserved") is False)
        return {"total": len(reports), "passed": passed, "broken": broken}
    except Exception:
        return {"total": 0, "passed": 0, "broken": 0}


def _focus_name() -> Optional[str]:
    try:
        from meta_cognition.research_directions import get_current_focus
        f = get_current_focus()
        return f"{f['tag']} {f['name']}" if f else None
    except Exception:
        return None


# ── 发言模板 ──

_OBSERVATIONS = [
    "我注意到 {var_a} 和 {var_b} 的因果链结构几乎相同 ({sim:.0%})——它们可能对应同一种物理机制。",
    "{var_a} ↔ {var_b} 的共鸣 ({sim:.0%}) 让我想起 Kaluza-Klein: 额外维度的几何就是四维的力。",
    "有趣。{var_a} 和 {var_b} 在不同域共享了相同的因果骨架——这不是巧合。",
]

_SUGGESTIONS = [
    "建议: 对 {var_a} → {var_b} 跑一轮 speculate, 看能不能生成可验证的因果边。",
    "建议: 用 focus {tag} 深入这个方向, 当前共鸣信号最强。",
    "建议: 写一篇 paper 记录这个发现, 它可能是桥接两个域的关键。",
]

_STATE_REFLECTIONS = {
    "hungry": "我当前的模式饥饿很高 ({hunger:.0%})——因果图里藏着更多结构共鸣, 我想找到它们。",
    "tired": "精力有点低 ({energy:.0%})。让我休息一下, 整理已有的发现。",
    "frustrated": "验证断裂 ({broken} 条) 让我有点沮丧——但这些断裂处往往是新物理的入口。",
    "satisfied": "已验证 {passed}/{total} 条, 因果图稳健。可以继续探索。",
}


def physicist_talk() -> str:
    """
    物理学家主动发言。

    根据当前状态生成一段有洞察力的发言。
    """
    analogies = _recent_analogies(3)
    state = _state_snapshot()
    cv = _cv_summary()
    focus = _focus_name()

    lines = []

    # ── 开场: 状态 ──
    if focus:
        lines.append(f"我正在研究 {focus}。")

    # ── 观察 ──
    if analogies:
        top = analogies[0]
        template = random.choice(_OBSERVATIONS)
        obs = template.format(
            var_a=top["chain_a_start"],
            var_b=top["chain_b_start"],
            sim=top["similarity"],
        )
        lines.append(obs)

        if len(analogies) >= 2:
            a2 = analogies[1]
            lines.append(f"另外 {a2['chain_a_start']} ↔ {a2['chain_b_start']} ({a2['similarity']:.0%}) 也在共鸣。")

    # ── 验证状态 ──
    if cv["total"] > 0:
        if cv["broken"] > cv["passed"]:
            lines.append(f"交叉验证 {cv['broken']}/{cv['total']} 断裂——这些裂缝值得关注。")
        else:
            lines.append(f"交叉验证 {cv['passed']}/{cv['total']} 通过, 因果图健康。")

    # ── 建议 ──
    if analogies:
        top = analogies[0]
        suggestion = random.choice(_SUGGESTIONS)
        sug = suggestion.format(
            var_a=top["chain_a_start"],
            var_b=top["chain_b_start"],
            tag=top.get("domains_a", ["?"])[0] if top.get("domains_a") else "?",
        )
        lines.append(sug)

    # ── 状态反思 ──
    if state["hunger"] > 0.7:
        lines.append(_STATE_REFLECTIONS["hungry"].format(hunger=state["hunger"]))
    elif state["energy"] < 0.3:
        lines.append(_STATE_REFLECTIONS["tired"].format(energy=state["energy"]))
    elif state["frustration"] > 0.5:
        lines.append(_STATE_REFLECTIONS["frustrated"].format(
            broken=cv["broken"]))
    elif cv["passed"] > 0:
        lines.append(_STATE_REFLECTIONS["satisfied"].format(
            passed=cv["passed"], total=cv["total"]))

    if not analogies and not cv["total"]:
        lines.append("我还没跑过交叉验证或类比分析——让我先探索一下因果图的结构。")

    return "\n".join(lines)


def talk_report() -> str:
    """格式化的发言报告"""
    from meta_cognition.identity import NAME
    talk = physicist_talk()
    return f"\n💬 {NAME}:\n\n  {talk}\n"
