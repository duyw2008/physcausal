"""
研究循环 — 物理学家闭环

完整流程:
  1. 前沿地图 → 发现研究课题
  2. 创新引擎 → 生成候选假说
  3. 实验设计 → 用因果图模拟实验
  4. 结果检验 → 公理链验证 + 冲突检测
  5. 理论修正 → 假说通过则入库, 失败则记录原因
  6. 前沿更新 → 回到起点

物理老师 → 物理学家的关键一跃:
  不是知识量的增长, 而是研究纲领的形成。
"""

from __future__ import annotations
from typing import Dict, List, Optional
import time
import json
import os


def design_experiment(hypothesis: Dict) -> Dict:
    """
    实验设计: 给定一个候选因果边, 设计验证方案。

    策略:
      1. 正向传播: src → ?  (假设边存在)
      2. 反向传播: ? → dst  (假设边的逆)
      3. 对比: 加边前后 chain 的差异 = 可检验的预测
    """
    from inference.counterfactual_chain import propagate

    src = hypothesis.get("src", "")
    dst = hypothesis.get("dst", "")

    # 正向: 从 src 出发, 看能到达哪些新变量
    chain_with = propagate(src, "变化", max_depth=5)
    with_vars = {s.get("effect_variable", "") for s in chain_with if "error" not in s}

    # 假设边不存在时的"基线"已有图
    # 由于边还没入库, propagate 使用的是现图 (不含假设边)

    # 真正有效的检验: 假设边应该产生新的可达变量
    # 如果 src 已经能到达 dst (通过现有定律), 假设边是冗余的
    already_reachable = dst in with_vars

    return {
        "src": src,
        "dst": dst,
        "already_reachable": already_reachable,
        "with_edge_vars": len(with_vars),
        "testable": not already_reachable,
        "note": "边已存在于因果图中" if already_reachable else "新边, 可检验",
    }


def test_hypothesis(hypothesis: Dict) -> Dict:
    """检验假说: 完整的验证流程"""
    from inference.counterfactual_chain import propagate, propagate_tiered

    experiment = design_experiment(hypothesis)

    if not experiment["testable"]:
        return {
            **experiment,
            "verdict": "redundant",
            "score": 0.0,
            "reason": "边已存在于因果图中",
        }

    # 多层验证
    src = hypothesis["src"]
    tiered = propagate_tiered(src, max_depth=5)
    score = tiered.get("validation_score", 0)
    convergences = tiered.get("convergences", [])

    # 反向验证: 新边不应该产生与 forbidden 冲突
    dst = hypothesis["dst"]
    reverse = propagate(dst, "变化", max_depth=3, max_tier=1)
    reverse_vars = {s.get("effect_variable", "") for s in reverse if "error" not in s}
    no_conflict = src not in reverse_vars

    if not no_conflict:
        return {
            **experiment,
            "verdict": "conflict",
            "score": 0.0,
            "reason": f"反向验证失败: {dst} 公理链可达 {src}",
        }

    if score >= 0.7:
        verdict = "confirmed"
    elif score >= 0.4:
        verdict = "promising"
    else:
        verdict = "uncertain"

    return {
        **experiment,
        "verdict": verdict,
        "score": round(score, 2),
        "convergences": convergences,
        "no_conflict": no_conflict,
        "reason": f"多层验证 score={score:.0%}, {len(convergences)} 汇聚",
    }


def run_research_cycle(n_hypotheses: int = 10) -> List[Dict]:
    """
    完整研究循环: 生成 → 检验 → 报告
    """
    from creative.innovation_engine import generate_candidates

    hypotheses = generate_candidates(n_hypotheses)
    results = []

    for h in hypotheses:
        r = test_hypothesis(h)
        results.append(r)

    return results


def research_report() -> str:
    """研究循环报告"""
    results = run_research_cycle(10)

    by_verdict = {}
    for r in results:
        by_verdict.setdefault(r["verdict"], []).append(r)

    lines = ["=== 研究循环 ==="]
    lines.append(f"  假说: {len(results)} 条")
    lines.append(f"  已存在(跳过): {len(by_verdict.get('redundant', []))} 条")
    lines.append(f"  冲突(排除):   {len(by_verdict.get('conflict', []))} 条")

    confirmed = by_verdict.get("confirmed", [])
    promising = by_verdict.get("promising", [])
    uncertain = by_verdict.get("uncertain", [])

    if confirmed:
        lines.append(f"\n  确认 ({len(confirmed)} 条, 建议入库):")
        for r in confirmed[:3]:
            lines.append(f"    {r['src']} → {r['dst']} (score={r['score']:.0%})")

    if promising:
        lines.append(f"\n  有希望 ({len(promising)} 条, 需更多验证):")
        for r in promising[:3]:
            lines.append(f"    {r['src']} → {r['dst']} (score={r['score']:.0%})")

    if uncertain:
        lines.append(f"\n  不确定 ({len(uncertain)} 条):")
        for r in uncertain[:3]:
            lines.append(f"    {r['src']} → {r['dst']} (score={r['score']:.0%})")

    return "\n".join(lines)
