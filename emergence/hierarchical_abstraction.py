"""
层次化抽象 v2 — 从微观变量中自动发现宏观序参量

方法论:
  1. 因果粗粒化 — 哪些微观变量有相同的因果下游？
  2. 信息瓶颈   — 压缩变量组为宏观抽象时保留了多少因果信息？
  3. 涌现检测   — 宏观变量是否具有成员个体不具备的预测力？

灵感: Wilson重整化群、Hoel因果涌现、Information Bottleneck
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import math


# ═══════════════════════════════════════════════════════════════
# 层 1: 因果粗粒化 — "哪些微观变量产生相同的宏观效应"
# ═══════════════════════════════════════════════════════════════

def _causal_neighborhood(var: str, depth: int = 2) -> Dict:
    """获取变量的因果邻域 (前因 + 后果)"""
    from physics.laws import library

    causes = set()
    effects = set()
    domains = set()

    # 直接出边和入边
    for law in library.list_all():
        all_vars = set(law.inputs + law.outputs)
        if var in law.inputs:
            for o in law.outputs:
                effects.add(o)
            domains.add(law.domain)
        if var in law.outputs:
            for i in law.inputs:
                causes.add(i)
            domains.add(law.domain)

    return {
        "variable": var,
        "causes": sorted(causes),
        "effects": sorted(effects),
        "domains": sorted(domains),
        "degree": len(causes) + len(effects),
    }


def causal_similarity(var_a: str, var_b: str) -> float:
    """
    两个变量的因果相似度 —— 它们的下游效应有多接近。
    如果 var_a 和 var_b 产生相同的效应变量，它们可能是同一个宏观量的微观表现。
    """
    na = _causal_neighborhood(var_a)
    nb = _causal_neighborhood(var_b)

    effects_a = set(na["effects"])
    effects_b = set(nb["effects"])

    if not effects_a or not effects_b:
        return 0.0

    intersection = effects_a & effects_b
    union = effects_a | effects_b

    # Jaccard on effects
    eff_sim = len(intersection) / len(union) if union else 0

    # 加分: 跨域的汇聚更值得关注
    domains_a = set(na["domains"])
    domains_b = set(nb["domains"])
    cross_domain_bonus = 0.3 if not domains_a.intersection(domains_b) else 0

    return round(min(eff_sim + cross_domain_bonus, 1.0), 3)


def find_causal_equivalence_classes(min_similarity: float = 0.5) -> List[Dict]:
    """
    找因果等价类: 从不同域出发、但产生相同下游效应的变量组。
    这是层次化抽象的候选 —— 它们可能是同一宏观量的微观表现。
    """
    from physics.laws import library, classify_variable

    # 只考虑派生变量 (基础变量已是"底层")
    candidates = []
    for law in library.list_all():
        for v in law.inputs + law.outputs:
            cat = classify_variable(v)
            if cat in ("derived",) and v not in candidates:
                candidates.append(v)

    # 取前30个高频的
    freq = defaultdict(int)
    for law in library.list_all():
        for v in set(law.inputs + law.outputs):
            freq[v] += 1
    candidates = sorted(candidates, key=lambda v: freq.get(v, 0), reverse=True)[:30]

    # 两两比较
    pairs = []
    for i, a in enumerate(candidates):
        for b in candidates[i + 1:]:
            sim = causal_similarity(a, b)
            if sim >= min_similarity:
                na = _causal_neighborhood(a)
                nb = _causal_neighborhood(b)

                # ── 过滤 trivial 对 ──
                # 同域 + 无新颖效应 → 跳过
                shared_domains = set(na["domains"]) & set(nb["domains"])
                all_same_domain = len(shared_domains) == len(set(na["domains"]) | set(nb["domains"]))
                shared_effects = set(na["effects"]) & set(nb["effects"])

                # 如果完全同域且没有跨域新奇效应，是平凡的
                if all_same_domain and len(shared_effects) <= 1:
                    continue

                # 必须有共享效应才有意义 (没有共享效应的等价类是噪声)
                if len(shared_effects) == 0:
                    continue

                # 必须是跨域的才有物理意义 (同域等价类是平凡的)
                if all_same_domain:
                    continue

                # 如果是同一个定律的输入/输出对 (如 m1/m2)，跳过
                from physics.laws import library as _lib
                same_law = False
                for law in _lib.list_all():
                    law_vars = set(law.inputs + law.outputs)
                    if a in law_vars and b in law_vars and len(law_vars) <= 4:
                        same_law = True
                        break
                if same_law and all_same_domain:
                    continue

                pairs.append({
                    "var_a": a,
                    "var_b": b,
                    "similarity": sim,
                    "domains_a": na["domains"],
                    "domains_b": nb["domains"],
                    "shared_effects": sorted(shared_effects)[:5],
                })

    return sorted(pairs, key=lambda x: x["similarity"], reverse=True)


# ═══════════════════════════════════════════════════════════════
# 层 2: 信息瓶颈 — 压缩变量组时保留了多少因果信息
# ═══════════════════════════════════════════════════════════════

def information_bottleneck_score(macro_name: str, micro_vars: List[str]) -> float:
    """
    信息瓶颈评分: 用宏观变量替代微观变量组时，保留了多少因果信息。

    度量: macro 能预测的因果效应 / micro 总共能预测的因果效应
    """
    from physics.laws import library

    # 微观变量的所有下游效应
    micro_effects = set()
    micro_domains = set()
    for v in micro_vars:
        nh = _causal_neighborhood(v)
        micro_effects.update(nh["effects"])
        micro_domains.update(nh["domains"])

    # 宏观变量名是否能"代表"这些效应
    # (在没有实际训练数据的情况下，用变量名语义重叠作为代理)
    macro_effects = set()
    for law in library.list_all():
        if macro_name in law.inputs or any(v in law.inputs for v in micro_vars):
            macro_effects.update(law.outputs)

    if not micro_effects:
        return 0.0

    compression_ratio = len(macro_effects & micro_effects) / len(micro_effects) if micro_effects else 0
    domain_diversity = len(micro_domains)

    # 跨域多且压缩率高的得分高
    score = compression_ratio * (1 + 0.2 * (domain_diversity - 1))
    return round(min(score, 1.0), 3)


# ═══════════════════════════════════════════════════════════════
# 层 3: 涌现检测 — 整体大于部分之和
# ═══════════════════════════════════════════════════════════════

def emergence_detection(macro_var: str, micro_vars: List[str]) -> Dict:
    """
    检测涌现: 宏观变量是否具有成员个体不具备的因果能力？

    三个信号:
      - 新奇出口: macro 单独能预测但 micro 都不能预测的效应
      - 汇聚入口: macro 被更多变量指向 (说明它是"吸引子")
      - 跨尺度: macro 和 micro 跨越了不同尺度 (经典↔量子, 微观↔宏观)
    """
    from physics.laws import library

    # micro 的所有效应
    micro_effects = set()
    for v in micro_vars:
        nh = _causal_neighborhood(v)
        micro_effects.update(nh["effects"])

    # macro 的效应
    macro_nh = _causal_neighborhood(macro_var)
    macro_effects = set(macro_nh["effects"])
    macro_causes = set(macro_nh["causes"])

    novel_effects = macro_effects - micro_effects

    # 汇聚度: 多少变量指向 macro
    convergence = len(macro_causes)

    # 跨尺度信号
    from physics.laws import classify_variable
    micro_cats = {classify_variable(v) for v in micro_vars}
    macro_cat = classify_variable(macro_var)
    cross_scale = macro_cat not in micro_cats

    emergence = (len(novel_effects) > 0) or (convergence >= 3 and cross_scale)

    return {
        "macro_var": macro_var,
        "micro_vars": micro_vars,
        "novel_effects": sorted(novel_effects)[:5],
        "convergence": convergence,
        "cross_scale": cross_scale,
        "emergence": emergence,
        "score": round(
            (len(novel_effects) * 0.4 + min(convergence / 5, 1) * 0.3 + (0.3 if cross_scale else 0)), 2
        ),
    }


# ═══════════════════════════════════════════════════════════════
# 综合: 发现涌现概念
# ═══════════════════════════════════════════════════════════════

def discover_abstractions(min_similarity: float = 0.3) -> List[Dict]:
    """
    三阶段流水线:
      1. 因果粗粒化 → 找等价类候选
      2. 信息瓶颈   → 评分压缩质量
      3. 涌现检测   → 确认新概念是否有整体大于部分之和的能力
    """
    # 阶段 1
    equiv_classes = find_causal_equivalence_classes(min_similarity)

    if not equiv_classes:
        return []

    # 阶段 2+3: 对每对候选，构造宏观变量名并评分
    discovered = []
    for eq in equiv_classes:
        micro_vars = [eq["var_a"], eq["var_b"]]
        # 自动命名
        macro_name = f"macro_{eq['var_a'][:8]}_{eq['var_b'][:8]}"

        ib_score = information_bottleneck_score(macro_name, micro_vars)
        emergence = emergence_detection(macro_name, micro_vars)

        total_score = (eq["similarity"] * 0.4 + ib_score * 0.3 + emergence["score"] * 0.3)

        discovered.append({
            "name": macro_name,
            "micro_vars": micro_vars,
            "causal_sim": eq["similarity"],
            "ib_score": ib_score,
            "emergence": emergence,
            "total_score": round(total_score, 3),
            "shared_effects": eq["shared_effects"],
            "domains": {"a": eq["domains_a"], "b": eq["domains_b"]},
        })

    return sorted(discovered, key=lambda x: x["total_score"], reverse=True)


def abstraction_report() -> str:
    """层次化抽象完整报告"""
    from physics.laws import library

    total_vars = len(set(
        v for law in library.list_all() for v in law.inputs + law.outputs
    ))

    lines = ["══════ 层次化抽象 v2 ══════"]
    lines.append(f"  变量池: {total_vars} | 定律: {len(library.list_all())}")
    lines.append("")

    discoveries = discover_abstractions(min_similarity=0.3)

    if not discoveries:
        lines.append("  未发现因果等价类 (min_sim=0.3)")
        lines.append("  可能原因: 变量在本体论上已足够清晰，不需要进一步粗粒化")
        return "\n".join(lines)

    lines.append(f"  因果等价类: {len(discoveries)} 对")
    lines.append("")

    for i, d in enumerate(discoveries[:8]):
        lines.append(f"  {i+1}. [{d['total_score']:.2f}] {d['name']}")
        lines.append(f"     微观: {d['micro_vars']}")
        lines.append(f"     因果相似: {d['causal_sim']:.0%} | IB压缩: {d['ib_score']:.0%} | 涌现: {d['emergence']['score']:.0%}")
        if d["shared_effects"]:
            lines.append(f"     共享效应: {d['shared_effects'][:3]}")
        if d["emergence"]["novel_effects"]:
            lines.append(f"     新奇效应: {d['emergence']['novel_effects'][:3]}")
        lines.append(f"     域: {d['domains']['a']} ↔ {d['domains']['b']}")
        lines.append("")

    lines.append(f"  (显示前 8 对，共 {len(discoveries)} 对)")

    return "\n".join(lines)
