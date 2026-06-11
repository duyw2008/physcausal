"""
形式化假设检验 — 贝叶斯证据聚合

替代启发式 tier 升级规则。
H0: 因果边 A→B 不存在
H1: 因果边 A→B 存在

证据来源:
  1. 公理链传播分数 (0-1)
  2. 跨域交叉验证 (通过率)
  3. 类比支持 (其他域同构数)
  4. 禁戒检查 (反向边是否 forbidden)
  5. 层级对比 (公理链 vs 全层级链)

聚合: Bayes 因子 BF = P(证据|H1) / P(证据|H0)
       BF > 3  → 支持升级
       BF < 1/3 → 支持降级
       1/3 < BF < 3 → 维持
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import math, json, os
from data_paths import data_path

_HYPOTHESIS_FILE = data_path("hypothesis_tests.json")

# ── 先验 ──
PRIOR_H1 = 0.3   # 先验: 30% 的候选边是真实存在的


def _load_tests() -> Dict:
    try:
        with open(_HYPOTHESIS_FILE) as f:
            return json.load(f)
    except:
        return {}


def _save_tests(tests: Dict):
    with open(_HYPOTHESIS_FILE, "w") as f:
        json.dump(tests, f, ensure_ascii=False, indent=2)


def _log_bayes_factor(p_h1_given_evidence: float, n_evidence: int) -> float:
    """对数 Bayes 因子, 避免数值下溢"""
    if p_h1_given_evidence <= 0 or p_h1_given_evidence >= 1:
        return 0.0
    posterior_odds = p_h1_given_evidence / (1 - p_h1_given_evidence)
    prior_odds = PRIOR_H1 / (1 - PRIOR_H1)
    return math.log(posterior_odds / prior_odds)


def _evidence_from_chain(discovery_name: str) -> float:
    """从公理链传播收集证据 (0-1 分数)"""
    try:
        from inference.counterfactual_chain import propagate_tiered
        from physics.laws import library
        # 找到这条发现
        for law in library.list_all():
            if law.name == discovery_name:
                inputs = law.inputs
                if inputs:
                    result = propagate_tiered(inputs[0], max_depth=5)
                    return result.get("validation_score", 0.5)
    except Exception:
        pass
    return 0.5  # 中性先验


def _evidence_from_cross_validation(discovery_name: str) -> Dict:
    """从交叉验证收集证据"""
    from data_paths import load_cv_summary
    cv = load_cv_summary()
    related = [r for r in cv if r.get("discovery") == discovery_name]
    
    if not related:
        return {"n": 0, "passed": 0, "score": 0.5}
    
    passed = sum(1 for r in related if r.get("convergence_preserved") is True)
    return {"n": len(related), "passed": passed, "score": passed / len(related)}


def _evidence_from_analogy(discovery_name: str) -> int:
    """从类比支持收集证据"""
    try:
        from creative.causal_analogy import find_causal_analogies
        analogies = find_causal_analogies(max_chains=15, min_similarity=0.5)
        support = 0
        for a in analogies:
            if discovery_name.lower() in str(a).lower():
                support += 1
        return support
    except:
        return 0


def _evidence_from_forbidden(discovery_name: str) -> float:
    """禁戒检查: 反向边是否被禁止"""
    try:
        from physics.laws import library
        for law in library.list_all():
            if law.name == discovery_name:
                # 如果有 forbidden_directions → 反向被禁止 → 正向更强
                if law.forbidden_directions:
                    return 0.9  # 强证据: 反向被禁止
                return 0.5  # 中性
    except:
        pass
    return 0.5


def test_hypothesis(discovery_name: str) -> Dict:
    """
    对一条发现执行形式化假设检验。

    返回: {bf, verdict, evidence, recommendation}
    """
    # 收集证据
    chain_score = _evidence_from_chain(discovery_name)
    cv_data = _evidence_from_cross_validation(discovery_name)
    analogy_support = _evidence_from_analogy(discovery_name)
    forbidden_score = _evidence_from_forbidden(discovery_name)

    # 聚合证据 (加权平均)
    weights = [0.3, 0.3, 0.2, 0.2]
    evidence_vec = [chain_score, cv_data["score"], 
                    min(analogy_support / 5.0, 1.0), forbidden_score]
    aggregated = sum(w * e for w, e in zip(weights, evidence_vec))

    # Bayes 因子
    log_bf = _log_bayes_factor(aggregated, cv_data["n"] + 1)

    # 判定
    if log_bf > 1.1:        # BF > 3
        verdict = "upgrade"
        tier_delta = +1
    elif log_bf < -1.1:     # BF < 1/3
        verdict = "downgrade"
        tier_delta = -1
    else:
        verdict = "maintain"
        tier_delta = 0

    result = {
        "discovery": discovery_name,
        "bayes_factor": round(math.exp(log_bf), 2),
        "log_bf": round(log_bf, 2),
        "verdict": verdict,
        "tier_delta": tier_delta,
        "evidence": {
            "chain_score": round(chain_score, 2),
            "cv_passed": f"{cv_data['passed']}/{cv_data['n']}",
            "cv_score": round(cv_data["score"], 2),
            "analogy_support": analogy_support,
            "forbidden": round(forbidden_score, 2),
        },
        "aggregated_score": round(aggregated, 2),
    }

    # 推荐额外实验
    if cv_data["n"] < 3:
        result["recommendation"] = "需更多交叉验证 (当前 n<3)"
    elif log_bf < 0.5 and log_bf > -0.5:
        result["recommendation"] = "证据不足 — 建议增加类比支持或补做量子域验证"
    elif verdict == "upgrade":
        result["recommendation"] = "证据充分 — 建议升级置信层级"
    else:
        result["recommendation"] = "维持现状"

    # 持久化
    tests = _load_tests()
    tests[discovery_name] = result
    _save_tests(tests)

    return result


def test_all_discoveries() -> List[Dict]:
    """对所有自动发现执行假设检验"""
    from data_paths import auto_laws_path
    with open(auto_laws_path()) as f:
        laws = json.load(f)
    
    results = []
    seen = set()
    for law in laws:
        name = law.get("name", "")
        if name in seen or not law.get("_chain_discovered"):
            continue
        seen.add(name)
        results.append(test_hypothesis(name))
    
    return results


def hypothesis_report() -> str:
    """假设检验报告"""
    results = test_all_discoveries()

    lines = ["═══ 形式化假设检验 ═══"]
    lines.append(f"  检验: {len(results)} 条发现")
    lines.append(f"  先验: P(H1) = {PRIOR_H1}")
    lines.append("")

    upgrade = [r for r in results if r["verdict"] == "upgrade"]
    downgrade = [r for r in results if r["verdict"] == "downgrade"]
    maintain = [r for r in results if r["verdict"] == "maintain"]

    lines.append(f"  升级: {len(upgrade)} | 降级: {len(downgrade)} | 维持: {len(maintain)}")
    lines.append("")

    for r in sorted(results, key=lambda x: x["bayes_factor"], reverse=True)[:8]:
        icon = "↑" if r["verdict"] == "upgrade" else "↓" if r["verdict"] == "downgrade" else "→"
        bar = "█" * min(int(r["aggregated_score"] * 10), 10)
        lines.append(f"  {icon} {r['discovery'][:30]}")
        lines.append(f"     BF={r['bayes_factor']:.1f} score={r['aggregated_score']:.2f} {bar}")
        lines.append(f"     cv={r['evidence']['cv_passed']} analogy={r['evidence']['analogy_support']} " + 
                     f"chain={r['evidence']['chain_score']:.2f}")
        lines.append(f"     → {r['recommendation']}")
        lines.append("")

    return "\n".join(lines)
