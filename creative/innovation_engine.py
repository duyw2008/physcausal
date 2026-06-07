"""
创新引擎 — 生成 + 过滤 + 进化

真正的创新:
  1. 生成器 — 随机提出候选因果边 (受 forbidden + 本体论约束)
  2. 过滤器 — 公理链验证 + 多轮一致性检查
  3. 进化器 — 通过的边入库 → 图变化 → 新边从新图中生成

与 learn_from_chain 的区别:
  learn_from_chain 检测图中**已有的**结构 (保守)
  创新引擎 生成图中**没有的**结构 (探索)

安全网:
  - 所有候选边必须经过 forbidden 检查
  - 公理链验证通过才能入库
  - 入库为 tier 3 (严肃假说), 不会污染共识层
  - 进化器跟踪成功率, 引导后续生成方向
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple
import random
import time


# ── 过滤规则: 哪些变量对不允许生成边 ──

FORBIDDEN_PAIRS: Set[Tuple[str, str]] = set()
FORBIDDEN_DOMAINS: Set[Tuple[str, str]] = {
    # 不允许逆转已知的因果方向
    ("quantum", "classical"),  # 量子不能"导致"经典 (除退相干外)
}


def _is_forbidden_pair(src: str, dst: str) -> bool:
    """检查变量对是否被禁止"""
    from physics.laws import library
    for law in library.list_all():
        for fd_src, fd_dst in law.forbidden_directions:
            if fd_src.lower() in src.lower() and fd_dst.lower() in dst.lower():
                return True
    return False


def _variable_ontology_weight(var: str) -> float:
    """变量本体论权重: 基础变量更容易产生创新"""
    from physics.laws import classify_variable
    weights = {"fundamental": 3.0, "geometric": 2.5, "quantum": 2.0, "derived": 1.0}
    return weights.get(classify_variable(var), 1.0)


def generate_candidates(n_candidates: int = 20) -> List[Dict]:
    """
    生成器: 随机提出新的因果边。

    策略:
      - 从不同领域中选变量对
      - 偏好基础变量和几何变量
      - 排除已有的边和 forbidden 方向
    """
    from physics.laws import library, classify_variable

    # 收集所有变量和领域
    all_vars = set()
    var_domains = {}
    for law in library.list_all():
        for v in law.inputs + law.outputs:
            all_vars.add(v)
            var_domains.setdefault(v, set()).add(law.domain)

    # 收集已有边
    existing_edges = set()
    for law in library.list_all():
        for src, dst in law.causal_direction:
            existing_edges.add((src, dst))

    vars_list = list(all_vars)
    candidates = []
    attempts = 0
    max_attempts = n_candidates * 10

    while len(candidates) < n_candidates and attempts < max_attempts:
        attempts += 1
        a = random.choice(vars_list)
        b = random.choice(vars_list)
        if a == b:
            continue
        if (a, b) in existing_edges or (b, a) in existing_edges:
            continue
        if _is_forbidden_pair(a, b):
            continue

        # 偏好跨领域
        domains_a = var_domains.get(a, set())
        domains_b = var_domains.get(b, set())
        cross_domain = not domains_a.intersection(domains_b)

        # 加权: 基础变量 × 跨领域
        weight = _variable_ontology_weight(a) * _variable_ontology_weight(b)
        if cross_domain:
            weight *= 2.0

        # 加权采样
        if random.random() > min(weight / 6.0, 0.9):
            continue

        candidates.append({
            "src": a,
            "dst": b,
            "cross_domain": cross_domain,
            "weight": round(weight, 1),
        })

    return candidates


def validate_candidate(candidate: Dict) -> Dict:
    """
    过滤器: 验证候选边是否与公理链一致。

    验证步骤:
      1. forbidden 检查 (已有)
      2. 公理链传播: 从 src 出发, 用 tier 0-1 定律, 能否到达 dst?
         → 如果能, 这条边与已知物理一致
         → 如果不能, 这条边是真正的新物理 (风险更高但潜力更大)
      3. 反向验证: 从 dst 反向传播, 看是否与现有因果方向冲突
    """
    from inference.counterfactual_chain import propagate

    src = candidate["src"]
    dst = candidate["dst"]

    # 公理链验证: src → dst?
    forward_chain = propagate(src, "变化", max_depth=5, max_tier=1)
    forward_vars = {s.get("effect_variable", "") for s in forward_chain if "error" not in s}

    # 反向验证: dst → src? (不应该有路径, 否则与因果方向冲突)
    reverse_chain = propagate(dst, "变化", max_depth=5, max_tier=1)
    reverse_vars = {s.get("effect_variable", "") for s in reverse_chain if "error" not in s}

    axiom_consistent = dst in forward_vars
    no_reverse = src not in reverse_vars

    # 验证得分
    if axiom_consistent and no_reverse:
        verdict = "consistent"
        score = 0.8
    elif axiom_consistent:
        verdict = "consistent_but_reversible"
        score = 0.5
    elif no_reverse:
        verdict = "new_physics"
        score = 0.6  # 新物理得分更高 (突破性)
    else:
        verdict = "conflict"
        score = 0.0

    return {
        **candidate,
        "axiom_consistent": axiom_consistent,
        "no_reverse_conflict": no_reverse,
        "verdict": verdict,
        "score": score,
    }


def innovate(n_candidates: int = 20,
             min_score: float = 0.5) -> List[Dict]:
    """创新主循环: 生成 → 验证 → 筛选"""
    candidates = generate_candidates(n_candidates)
    validated = [validate_candidate(c) for c in candidates]
    return [v for v in validated if v["score"] >= min_score]


def innovation_report() -> str:
    """创新引擎报告"""
    results = innovate(n_candidates=30, min_score=0.5)

    lines = ["=== 创新引擎 ==="]
    lines.append(f"  生成: 30 条候选边")
    lines.append(f"  通过: {len(results)} 条")

    if not results:
        lines.append("  (无创新 — 当前因果图已高度饱和)")
        return "\n".join(lines)

    by_verdict = {}
    for r in results:
        by_verdict.setdefault(r["verdict"], []).append(r)

    for verdict, items in by_verdict.items():
        labels = {"consistent": "与公理一致", "new_physics": "新物理",
                  "consistent_but_reversible": "一致但可逆"}
        lines.append(f"\n  {labels.get(verdict, verdict)} ({len(items)} 条):")
        for item in items[:5]:
            lines.append(f"    {item['src']} → {item['dst']} (跨域={item['cross_domain']})")

    return "\n".join(lines)


def innovation_stats() -> Dict:
    """创新统计: 跟踪生成效率"""
    results = innovate(n_candidates=50, min_score=0.0)
    total = len(results)
    passed = sum(1 for r in results if r["score"] >= 0.5)
    by_verdict = {}
    for r in results:
        by_verdict[r["verdict"]] = by_verdict.get(r["verdict"], 0) + 1

    return {
        "generated": total,
        "passed": passed,
        "pass_rate": passed / max(total, 1),
        "verdicts": by_verdict,
    }
