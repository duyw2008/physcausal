"""
增量学习记忆 — 诺特的长期记忆

记录每一次发现尝试、结果、模式，越学越聪明。

三类记录:
  hypothesis:  假说提案 → {confirmed, rejected, forbidden_blocked, pending}
  analogy:     类比发现 → {solid, speculative, false_positive}
  exploration: 探索方向 → {fruitful, barren, unknown}

每轮 consolidate() 抽取模式，校准未来置信度。
"""

from __future__ import annotations
import json, os, time
from typing import Dict, List, Optional
from collections import defaultdict


MEMORY_PATH = None


def _memory_path() -> str:
    global MEMORY_PATH
    if MEMORY_PATH is None:
        MEMORY_PATH = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "learning_memory.json"
        )
    return MEMORY_PATH


def _load() -> List[Dict]:
    path = _memory_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return []


def _save(records: List[Dict]):
    path = _memory_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 只保留最近 500 条
    with open(path, "w") as f:
        json.dump(records[-500:], f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════
# 记录
# ═══════════════════════════════════════════════

def record_hypothesis(var_a: str, var_b: str, confidence: float, 
                       outcome: str, note: str = ""):
    """记录一个假说提案的结果"""
    records = _load()
    records.append({
        "type": "hypothesis",
        "time": time.time(),
        "var_a": var_a, "var_b": var_b,
        "confidence": confidence, "outcome": outcome,
        "note": note,
    })
    _save(records)


def record_analogy(chain_a: str, chain_b: str, similarity: float,
                    quality: str, insight: str = ""):
    """记录一个类比发现"""
    records = _load()
    records.append({
        "type": "analogy",
        "time": time.time(),
        "chain_a": chain_a, "chain_b": chain_b,
        "similarity": similarity, "quality": quality,
        "insight": insight[:120],
    })
    _save(records)


def record_exploration(direction: str, outcome: str, discoveries: int = 0):
    """记录探索方向的结果"""
    records = _load()
    records.append({
        "type": "exploration",
        "time": time.time(),
        "direction": direction,
        "outcome": outcome,
        "discoveries": discoveries,
    })
    _save(records)


# ═══════════════════════════════════════════════
# 查询 / 学习
# ═══════════════════════════════════════════════

def has_been_tried(var_a: str, var_b: str) -> Optional[str]:
    """这对变量之前被提案过吗？返回 outcome 或 None"""
    records = _load()
    pair = {var_a, var_b}
    for r in records:
        if r["type"] == "hypothesis":
            if {r["var_a"], r["var_b"]} == pair:
                return r.get("outcome", "unknown")
    return None


def should_skip(var_a: str, var_b: str) -> bool:
    """这对是否应该跳过（已证实不好）"""
    outcome = has_been_tried(var_a, var_b)
    return outcome in ("rejected", "forbidden_blocked")


def calibrate_confidence(var_a: str, var_b: str, base_conf: float) -> float:
    """
    基于历史校准置信度。
    - 如果这对之前被 rejected → 降 50%
    - 如果类似的变量对类型多次成功 → 微升 10%
    """
    from physics.laws import classify_variable

    # 同对检查
    outcome = has_been_tried(var_a, var_b)
    if outcome == "rejected":
        return base_conf * 0.5
    if outcome == "confirmed":
        return min(base_conf * 1.1, 1.0)

    # 同类型对成功率
    records = _load()
    cat_a = classify_variable(var_a)
    cat_b = classify_variable(var_b)
    
    same_type = 0
    same_type_success = 0
    for r in records:
        if r["type"] != "hypothesis":
            continue
        ra, rb = r["var_a"], r["var_b"]
        if classify_variable(ra) == cat_a and classify_variable(rb) == cat_b:
            same_type += 1
            if r.get("outcome") == "confirmed":
                same_type_success += 1
    
    if same_type >= 3 and same_type_success / same_type >= 0.5:
        return min(base_conf * 1.15, 1.0)
    
    return base_conf


# ═══════════════════════════════════════════════
# 巩固
# ═══════════════════════════════════════════════

def consolidate() -> Dict:
    """
    抽取学习模式。返回:
      {total_records, success_rate, top_patterns, recommendations}
    """
    records = _load()
    if not records:
        return {"total_records": 0, "success_rate": 0, "patterns": [], "recommendations": []}

    # 成功率
    hyps = [r for r in records if r["type"] == "hypothesis"]
    confirmed = sum(1 for h in hyps if h.get("outcome") == "confirmed")
    rejected = sum(1 for h in hyps if h.get("outcome") in ("rejected", "forbidden_blocked"))
    success_rate = confirmed / len(hyps) if hyps else 0

    # 成功模式: 哪些变量类别对最容易成功
    from physics.laws import classify_variable
    pair_success = defaultdict(lambda: [0, 0])  # {cat_pair: [success, total]}
    for h in hyps:
        ca = classify_variable(h["var_a"])
        cb = classify_variable(h["var_b"])
        key = tuple(sorted([ca, cb]))
        pair_success[key][1] += 1
        if h.get("outcome") == "confirmed":
            pair_success[key][0] += 1

    patterns = []
    for (ca, cb), (s, t) in sorted(pair_success.items(), key=lambda x: -x[1][0] / max(x[1][1], 1)):
        if t >= 3:
            rate = s / t
            patterns.append({
                "categories": f"{ca}↔{cb}",
                "success_rate": round(rate, 2),
                "samples": t,
            })

    # 推荐
    recommendations = []
    if success_rate < 0.1 and len(hyps) > 5:
        recommendations.append("假说成功率低——检查 forbidden 过滤是否过松")
    if patterns:
        best = patterns[0]
        recommendations.append(f"最成功的变量对类型: {best['categories']} ({best['success_rate']:.0%}, {best['samples']}例)")

    return {
        "total_records": len(records),
        "hypothesis_count": len(hyps),
        "success_rate": round(success_rate, 2),
        "confirmed": confirmed,
        "rejected": rejected,
        "patterns": patterns[:5],
        "recommendations": recommendations,
    }


def learning_report() -> str:
    """学习记忆报告"""
    c = consolidate()
    lines = ["══════ 增量学习 ══════"]
    lines.append(f"  总记录: {c['total_records']}")
    lines.append(f"  假说: {c['hypothesis_count']} (通过:{c['confirmed']} 拒绝:{c['rejected']})")
    lines.append(f"  成功率: {c['success_rate']:.0%}")
    
    if c["patterns"]:
        lines.append(f"\n  成功模式:")
        for p in c["patterns"][:3]:
            lines.append(f"    {p['categories']} — {p['success_rate']:.0%} ({p['samples']}例)")
    
    if c["recommendations"]:
        lines.append(f"\n  建议:")
        for r in c["recommendations"]:
            lines.append(f"    • {r}")
    
    return "\n".join(lines)
