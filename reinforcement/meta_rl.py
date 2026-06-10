"""
元强化学习 — 主导物理学家的行为策略

不是驱动力微调, 而是从 session 历史中学习:
  - 哪个研究方向产出最高?
  - 探索 vs 利用的最优平衡?
  - 何时切换方向?
  - 精力如何最优分配?
"""

from __future__ import annotations
from typing import Dict, List, Tuple
import json, os, time, math
from data_paths import data_path

_RECORD_FILE = data_path("research_record.json")
_EXPLORE_RATE = 0.2  # epsilon-greedy 基础探索率


def _load_records() -> List[Dict]:
    try:
        with open(_RECORD_FILE) as f:
            return json.load(f)
    except:
        return []


def _save_records(records: List[Dict]):
    with open(_RECORD_FILE, "w") as f:
        json.dump(records[-200:], f, ensure_ascii=False)


def log_action(action: str, outcome: Dict):
    """记录一次研究行动及其结果"""
    records = _load_records()
    records.append({
        "time": time.time(),
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "action": action,
        "outcome": outcome,
    })
    _save_records(records)


def _ucb_score(counts: Dict[str, int], values: Dict[str, float],
               total: int, action: str) -> float:
    """UCB1 上置信界 — 平衡探索与利用"""
    if counts.get(action, 0) == 0:
        return float("inf")  # 没试过的动作优先级最高
    exploit = values.get(action, 0.5)
    explore = math.sqrt(2 * math.log(max(total, 1)) / counts[action])
    return exploit + explore


def best_strategy() -> Dict:
    """
    从历史记录中学习最优策略。

    返回: {recommended_action, confidence, rationale}
    """
    records = _load_records()
    if len(records) < 10:
        return {
            "action": "explore",
            "strategy": "explore_first",
            "rationale": "历史不足, 均匀探索所有动作",
        }

    # 聚合统计数据
    counts: Dict[str, int] = {}
    values: Dict[str, float] = {}  # 平均回报 (发现率)

    for r in records:
        action = r.get("action", "unknown")
        outcome = r.get("outcome", {})
        reward = outcome.get("discoveries", 0) * 2 + outcome.get("analogies", 0) * 0.5 + outcome.get("validations", 0) * 0.3

        counts[action] = counts.get(action, 0) + 1
        old_val = values.get(action, 0)
        n = counts[action]
        values[action] = old_val + (reward - old_val) / n

    total = sum(counts.values())

    # UCB 选择最优动作
    actions = list(counts.keys())
    if not actions:
        return {"action": "explore", "strategy": "no_data",
                "rationale": "无历史数据"}

    best = max(actions, key=lambda a: _ucb_score(counts, values, total, a))

    # 如果最佳动作的探索值 > 利用值, 建议探索新方向
    best_exploit = values.get(best, 0.5)
    best_explore = math.sqrt(2 * math.log(total) / counts[best]) if counts[best] > 0 else 1.0

    if best_explore > best_exploit * 2:
        strategy = "explore"
        rationale = f"{best} 利用值 {best_exploit:.2f} 低, 探索收益 {best_explore:.2f} 高"
    else:
        strategy = "exploit"
        rationale = f"{best} 利用值 {best_exploit:.2f} 稳定 (n={counts[best]})"

    return {
        "action": best,
        "strategy": strategy,
        "confidence": best_exploit,
        "counts": dict(counts),
        "values": {k: round(v, 2) for k, v in values.items()},
        "rationale": rationale,
    }


def strategy_report() -> str:
    """策略优化报告"""
    s = best_strategy()

    lines = ["═══ 元RL 策略优化 ═══"]
    lines.append(f"  推荐动作: {s['action']}")
    lines.append(f"  策略: {s['strategy']} (UCB={s.get('confidence', 0):.2f})")
    lines.append(f"  {s['rationale']}")

    if s.get("counts"):
        lines.append("")
        lines.append("  动作统计:")
        for act, count in sorted(s["counts"].items(), key=lambda x: x[1], reverse=True):
            val = s["values"].get(act, 0)
            bar = "█" * int(val * 10) + "░" * (10 - int(val * 10))
            lines.append(f"    {act:<20s} n={count:<4d} V={val:.2f} {bar}")

    return "\n".join(lines)
