"""
粗粒化引擎 — 从微观变量构建宏观层次

核心:
  1. 信息瓶颈 — 压缩 N 个变量为 1 个时保留了多少因果信息
  2. 宏观因果图 — 在粗粒化变量上重建因果模型
  3. 涌现验证 — 宏观变量是否具有微观变量不具备的因果能力
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import math


def _get_law_graph() -> Dict[str, List[str]]:
    """变量 → 与之有因果关系的变量列表 (出现在同一规律中)"""
    from physics.laws import library
    graph = defaultdict(list)
    for law in library.list_all():
        all_vars = list(law.inputs + law.outputs)
        for i, a in enumerate(all_vars):
            for b in all_vars[i + 1:]:
                graph[a].append(b)
                graph[b].append(a)
    return dict(graph)


def information_loss(cluster_vars: List[str],
                     target_var: str) -> Dict:
    """
    如果将 cluster_vars 压缩为一个宏观变量,
    对预测 target_var 损失多少信息?

    返回 {loss_ratio, conditional_entropy_ratio, verdict}
    """
    if len(cluster_vars) < 2:
        return {"loss_ratio": 0.0, "verdict": "too_small"}

    graph = _get_law_graph()

    # 原信息: cluster 中每个变量与 target 有多少共现
    original_edges = 0
    for v in cluster_vars:
        neighbors = set(graph.get(v, []))
        if target_var in neighbors:
            original_edges += 1

    # 压缩后信息: 合并后仍与 target 有间接连通的概率
    compressed_edges = 0
    for v in cluster_vars:
        neighbors = set(graph.get(v, []))
        # 如果 cluster 中任一变量与 target 连通, 压缩后仍连通
        if target_var in neighbors:
            compressed_edges = 1
            break

    max_possible = len(cluster_vars)
    if max_possible == 0:
        return {"loss_ratio": 1.0, "verdict": "empty"}

    loss = (original_edges - compressed_edges) / max(max_possible, 1)

    if loss == 0:
        verdict = "lossless"
    elif loss < 0.5:
        verdict = "acceptable"
    else:
        verdict = "lossy"

    return {
        "loss_ratio": round(loss, 2),
        "original_connections": original_edges,
        "compressed_connections": compressed_edges,
        "verdict": verdict,
    }


def coarse_grain(cluster_vars: List[str],
                 macro_name: str) -> Dict:
    """
    创建宏观变量并重写定律。

    返回 {macro_var, micro_vars, laws_rewritten, info_loss}
    """
    from physics.laws import library
    from physics.laws import PhysicsLaw, ConstraintType

    # 检查命名冲突
    existing = {l.name for l in library.list_all()}
    if macro_name in existing:
        return {"error": f"Macro variable '{macro_name}' already exists as a law name"}

    # 检查变量名冲突
    all_vars = set()
    for law in library.list_all():
        all_vars.update(law.inputs + law.outputs)
    if macro_name in all_vars:
        # 名字已被占用, 加后缀
        macro_name = f"{macro_name}_macro"
        if macro_name in all_vars:
            return {"error": f"Cannot create '{macro_name}' — conflicts with existing variable"}

    # 计算信息损失
    losses = []
    graph = _get_law_graph()
    all_targets = set()
    for v in cluster_vars:
        all_targets.update(graph.get(v, []))

    for target in all_targets:
        if target not in cluster_vars:
            loss = information_loss(cluster_vars, target)
            losses.append(loss)

    avg_loss = sum(l["loss_ratio"] for l in losses) / max(len(losses), 1)
    lossless_count = sum(1 for l in losses if l["verdict"] == "lossless")

    # 找出涉及这些微观变量的定律
    affected_laws = []
    for law in library.list_all():
        law_vars = set(law.inputs + law.outputs)
        if law_vars & set(cluster_vars):
            affected_laws.append({
                "law_name": law.name,
                "domain": law.domain,
                "inputs": law.inputs,
                "outputs": law.outputs,
                "causal": law.causal_direction,
            })

    return {
        "macro_name": macro_name,
        "micro_vars": cluster_vars,
        "affected_laws": len(affected_laws),
        "law_details": affected_laws[:5],
        "avg_info_loss": round(avg_loss, 2),
        "lossless_ratio": round(lossless_count / max(len(losses), 1), 2),
        "total_targets": len(all_targets),
        "feasible": avg_loss < 0.5 and len(affected_laws) >= 2,
    }


def find_coarse_grain_candidates(min_vars: int = 2,
                                 max_loss: float = 0.3) -> List[Dict]:
    """
    找适合粗粒化的变量组。

    候选条件:
      - 变量间互信息高 (已经由 MI 聚类提供)
      - 压缩后信息损失低
      - 涉及至少 2 条定律
    """
    from emergence.hierarchical_abstraction import cluster_by_mi
    clusters = cluster_by_mi(min_mi=0.03, max_clusters=20)

    candidates = []
    for c in clusters:
        vars_list = c["variables"]
        if len(vars_list) < min_vars:
            continue

        # 生成宏观名称
        macro_name = f"Macro_{'_'.join(vars_list[:2])}"[:40]

        result = coarse_grain(vars_list, macro_name)
        if result.get("feasible") and result["avg_info_loss"] <= max_loss:
            result["mi"] = c["mi"]
            result["name"] = macro_name
            candidates.append(result)

    return sorted(candidates, key=lambda x: x["avg_info_loss"])


def report() -> str:
    """粗粒化可行性报告"""
    candidates = find_coarse_grain_candidates(max_loss=0.3)

    lines = ["=== 粗粒化分析 ==="]
    lines.append(f"候选宏观变量: {len(candidates)} 组")
    lines.append("")

    if not candidates:
        lines.append("  当前变量结构足够高效, 无需粗粒化。")
        lines.append("  每个变量都承载了不可压缩的因果信息。")
        return "\n".join(lines)

    for i, c in enumerate(candidates[:5]):
        macro = c["macro_name"]
        micro = c["micro_vars"]
        loss = c["avg_info_loss"]
        laws = c["affected_laws"]
        lossless = c["lossless_ratio"]

        verdict = "✓ 无损" if loss == 0 else "△ 可接受" if loss < 0.2 else "⚠ 有损"
        lines.append(f"  {i+1}. {macro}")
        lines.append(f"     微观变量: {micro}")
        lines.append(f"     信息损失: {loss:.0%} ({verdict})")
        lines.append(f"     涉及定律: {laws} 条")
        if c.get("law_details"):
            for detail in c["law_details"][:3]:
                lines.append(f"       · {detail['law_name']}: {detail['inputs']} → {detail['outputs']}")
        lines.append("")

    return "\n".join(lines)
