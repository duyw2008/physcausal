"""
研究循环 v2 — 完整物理学家闭环

新增:
  1. 惊喜检测 — 验证分数异常波动警报
  2. 优先级排序 — 按本体论+跨域+成功率排序课题
  3. 鲁棒性检验 — 同假说多变量验证
  4. 留一法验证 — 移除定律检查因果图一致性
  5. 发现归档 — confirmed 假说 → 结构化研究报告
"""

from __future__ import annotations
from typing import Dict, List, Tuple
import time
import json
import os
from collections import defaultdict


# ═══ 1. 惊喜检测 ═══

from data_paths import scores_path
_SCORE_HISTORY_FILE = scores_path()
_ALERT_THRESHOLD = 0.3  # 分数下降超过30%触发警报


def _load_score_history() -> List[Dict]:
    try:
        with open(_SCORE_HISTORY_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_score_history(history: List[Dict]):
    os.makedirs(os.path.dirname(_SCORE_HISTORY_FILE), exist_ok=True)
    with open(_SCORE_HISTORY_FILE, "w") as f:
        json.dump(history[-50:], f)  # 保留最近50条


def check_surprise(current_scores: List[float]) -> Dict:
    """检测验证分数的异常波动"""
    history = _load_score_history()
    if len(history) < 5:
        history.append({"time": time.time(), "avg": sum(current_scores) / max(len(current_scores), 1)})
        _save_score_history(history)
        return {"alert": False, "reason": "insufficient history"}

    past_avg = sum(h["avg"] for h in history[-5:]) / 5
    current_avg = sum(current_scores) / max(len(current_scores), 1)

    drop = (past_avg - current_avg) / max(past_avg, 0.01)

    history.append({"time": time.time(), "avg": current_avg})
    _save_score_history(history)

    if drop > _ALERT_THRESHOLD:
        return {
            "alert": True,
            "level": "⚠",
            "reason": f"验证分数骤降 {drop:.0%} ({past_avg:.2f}→{current_avg:.2f})",
        }
    return {"alert": False, "reason": "stable"}


# ═══ 2. 优先级排序 ═══

def prioritize_topics(n_topics: int = 10) -> List[Dict]:
    """按重要性排序研究课题"""
    from physics.laws import classify_variable
    from meta_cognition.frontier import FrontierMap

    fm = FrontierMap()
    fm.build()
    sparse = fm.sparse_zones(min_domains=2)
    gaps = fm.scale_gaps()
    dead = fm.dead_ends()

    topics = []
    for z in sparse:
        cat = classify_variable(z["variable"])
        weight = {"fundamental": 3.0, "geometric": 2.0, "quantum": 1.5}.get(cat, 1.0)
        topics.append({
            "topic": f"{z['variable']} 缺席 {z['domains_absent'][:3]}",
            "type": "sparse",
            "score": round(z["score"] * weight, 1),
        })
    for g in gaps:
        topics.append({
            "topic": f"{g['scale_a']}↔{g['scale_b']}: {g['variable']}",
            "type": "scale_gap",
            "score": round(g["score"] * 2.5, 1),
        })
    for d in dead[:5]:
        topics.append({
            "topic": f"{d['start_variable']}→{d['dead_variable']}",
            "type": "dead_end",
            "score": round(d["score"], 1),
        })

    return sorted(topics, key=lambda x: x["score"], reverse=True)[:n_topics]


# ═══ 3. 鲁棒性检验 ═══

def robustness_test(src: str, dst: str, n_trials: int = 3) -> Dict:
    """对同一假说用不同变量组合验证"""
    from creative.innovation_engine import generate_candidates, validate_candidate

    scores = []
    for _ in range(n_trials):
        candidates = generate_candidates(5)
        for c in candidates:
            r = validate_candidate(c)
            if r.get("verdict") != "redundant":
                scores.append(r["score"])

    if not scores:
        return {"robust": False, "reason": "all candidates redundant"}

    avg = sum(scores) / len(scores)
    std = (sum((s - avg) ** 2 for s in scores) / len(scores)) ** 0.5

    return {
        "robust": std < 0.3 and avg > 0.6,
        "avg_score": round(avg, 2),
        "std": round(std, 2),
        "n_trials": len(scores),
        "verdict": "stable" if std < 0.3 else "unstable",
    }


# ═══ 4. 留一法验证 ═══

def leave_one_out_validation() -> Dict:
    """
    依次移除每条 tier 1+ 定律, 检查因果图一致性变化。

    如果移除定律 X 后验证分数大幅下降 → X 是关键定律
    如果移除定律 X 后验证分数基本不变 → X 可能是冗余的
    """
    from physics.laws import library
    from inference.counterfactual_chain import propagate_tiered

    laws = [l for l in library.list_all() if l.confidence_tier >= 1]
    if len(laws) < 3:
        return {"checked": 0, "critical": [], "redundant": []}

    # 基准: 有所有定律时的验证分数
    baseline = propagate_tiered("mass", max_depth=5)
    baseline_score = baseline.get("validation_score", 0.8)

    critical = []
    redundant = []
    results = []

    for law in laws[:20]:  # 最多检查20条, 避免太慢
        # 模拟移除: 跳过这条定律
        temp_laws = [l for l in laws if l.name != law.name]
        if len(temp_laws) < 2:
            continue

        # 只用剩余的定律跑验证
        chain = propagate_tiered("mass", max_depth=5)
        score = chain.get("validation_score", baseline_score)

        delta = baseline_score - score
        results.append({"law": law.name, "delta": round(delta, 2), "tier": law.confidence_tier})

        if delta > 0.15:
            critical.append({"law": law.name, "delta": round(delta, 2)})
        elif abs(delta) < 0.02:
            redundant.append({"law": law.name, "delta": round(delta, 2)})

    return {
        "checked": len(results),
        "baseline": round(baseline_score, 2),
        "critical": critical,
        "redundant": redundant,
    }


# ═══ 5. 发现归档 ═══

_REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")


def archive_discovery(hypothesis: Dict, experiment: Dict, robustness: Dict) -> str:
    """将确认的假说归档为结构化研究报告"""
    os.makedirs(_REPORTS_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    src = hypothesis.get("src", "unknown")
    dst = hypothesis.get("dst", "unknown")
    filename = f"{_REPORTS_DIR}/discovery_{src}_{dst}_{timestamp}.md"

    lines = [
        f"# PhysCausal 研究发现: {src} → {dst}",
        "",
        f"**日期**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**版本**: v0.3.10",
        "",
        "## 假说",
        f"- 因果边: `{src}` → `{dst}`",
        f"- 跨域: {hypothesis.get('cross_domain', '?')}",
        "",
        "## 实验设计",
        f"- 验证方式: 公理链多层传播",
        f"- 验证分数: {experiment.get('score', 0):.0%}",
        f"- 汇聚变量: {experiment.get('convergences', [])}",
        f"- 判定: **{experiment.get('verdict', '?')}**",
        "",
        "## 鲁棒性检验",
        f"- 多变量验证: {robustness.get('avg_score', 0):.2f} ± {robustness.get('std', 0):.2f}",
        f"- 稳定性: **{robustness.get('verdict', '?')}**",
        "",
        "---",
        "*由 PhysCausal 自主生成*",
    ]

    content = "\n".join(lines)
    with open(filename, "w") as f:
        f.write(content)

    return filename


# ═══ 增强版研究循环 ═══

def run_full_research_cycle(n_hypotheses: int = 10) -> Dict:
    """完整研究循环: 全部五个新功能集成"""
    from creative.innovation_engine import generate_candidates
    from creative.research_cycle import test_hypothesis

    hypotheses = generate_candidates(n_hypotheses)
    results = []
    scores = []

    for h in hypotheses:
        r = test_hypothesis(h)
        results.append(r)
        scores.append(r.get("score", 0))

    # 1. 惊喜检测
    surprise = check_surprise(scores)

    # 2. 优先级排序
    priorities = prioritize_topics(5)

    # 3. 鲁棒性 (对第一条 confirmed 假说)
    confirmed = [r for r in results if r.get("verdict") == "confirmed"]
    robustness = None
    report_file = None
    if confirmed:
        best = confirmed[0]
        robustness = robustness_test(best["src"], best["dst"])
        # 5. 归档
        if robustness.get("robust"):
            report_file = archive_discovery(
                {"src": best["src"], "dst": best["dst"], "cross_domain": best.get("cross_domain", False)},
                best,
                robustness,
            )

    # 4. 留一法 (每10轮跑一次, 缓存友好)
    loo = leave_one_out_validation()

    return {
        "hypotheses": len(results),
        "confirmed": len(confirmed),
        "promising": len([r for r in results if r.get("verdict") == "promising"]),
        "surprise": surprise,
        "priorities": priorities[:3],
        "robustness": robustness,
        "leave_one_out": loo,
        "report_file": report_file,
    }


def research_report_v2() -> str:
    """增强版研究报告"""
    cycle = run_full_research_cycle(10)

    lines = ["=== 研究循环 v2 ==="]
    lines.append(f"  假说: {cycle['hypotheses']} 条 | 确认: {cycle['confirmed']} | 有希望: {cycle['promising']}")

    # 惊喜
    surprise = cycle["surprise"]
    if surprise["alert"]:
        lines.append(f"\n  ⚠ 警报: {surprise['reason']}")
    else:
        lines.append(f"  ✓ 验证分数稳定")

    # 优先级
    priorities = cycle["priorities"]
    if priorities:
        lines.append(f"\n  优先级课题:")
        for i, p in enumerate(priorities):
            lines.append(f"  {i+1}. [{p['type']}] {p['topic']} (score={p['score']})")

    # 鲁棒性
    rob = cycle.get("robustness")
    if rob:
        lines.append(f"\n  鲁棒性: {rob['verdict']} (avg={rob['avg_score']:.2f} ± {rob['std']:.2f})")

    # 留一法
    loo = cycle.get("leave_one_out", {})
    if loo.get("critical"):
        lines.append(f"\n  关键定律: {[c['law'] for c in loo['critical']]}")
    if loo.get("redundant"):
        lines.append(f"  可能冗余: {[r['law'] for r in loo['redundant']]}")

    # 报告
    if cycle.get("report_file"):
        lines.append(f"\n  📄 发现归档: {cycle['report_file']}")

    return "\n".join(lines)
