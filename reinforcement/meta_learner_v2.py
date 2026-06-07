"""
元学习 v2 — 从发现中提取模式模板, 跨领域迁移

核心:
  1. 模式模板 — 从一次成功的发现中提取可泛化的因果模式
  2. 模板匹配 — 在新领域中搜索同样的模式
  3. 跨域迁移 — 在 mechanics 发现的汇聚, 在 optics 搜索同类

与 v1 (MetaLearner) 的区别:
  v1 基于 Q-table 迁移 (env→env)
  v2 基于因果图模式迁移 (domain→domain)
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple
from collections import defaultdict


def extract_convergence_template(discovery_variables: List[str],
                                 discovery_domains: List[str]) -> Dict:
    """
    从一次汇聚发现中提取可泛化的模式模板。

    例如: [kinetic_energy, energy] → geodesic_path
    模板: {pattern: "two_inputs_one_output",
            input_count: 2, output_count: 1,
            domains: [mechanics, modern, unification]}
    """
    return {
        "pattern": "convergence",
        "input_count": len(discovery_variables) - 1 if len(discovery_variables) > 1 else 1,
        "output_count": min(1, len(discovery_variables)),
        "input_vars": discovery_variables[:-1],
        "output_var": discovery_variables[-1] if discovery_variables else "",
        "domains": list(set(discovery_domains)),
    }


def search_similar_patterns(template: Dict,
                            min_inputs: int = 2) -> List[Dict]:
    """
    在因果图中搜索与模板相似的模式。

    对每个变量:
      - 找所有以该变量为 output 的定律
      - 如果 input_count >= min_inputs → 候选汇聚
    """
    from physics.laws import library
    from inference.counterfactual_chain import build_dependency_graph

    graph = build_dependency_graph()
    results = []

    for law in library.list_all():
        if law.confidence_tier >= 4:  # 跳过探索性定律
            continue
        if law.domain in template.get("domains", []):  # 跳过已覆盖的领域
            continue

        # 找以 law 的输出为目标的汇聚
        for output_var in law.outputs:
            # 这个输出变量作为多少个其他定律的输出?
            inputs_to_this = []
            for other_law in library.list_all():
                if other_law.name == law.name:
                    continue
                if output_var in other_law.outputs:
                    inputs_to_this.append({
                        "law": other_law.name,
                        "domain": other_law.domain,
                        "inputs": other_law.inputs,
                    })

            if len(inputs_to_this) >= min_inputs:
                domains_involved = set()
                domains_involved.add(law.domain)
                for entry in inputs_to_this:
                    domains_involved.add(entry["domain"])

                # 检查是否跨领域
                if len(domains_involved) >= 2:
                    results.append({
                        "output_var": output_var,
                        "converging_laws": len(inputs_to_this),
                        "domains": sorted(domains_involved),
                        "template_match": "convergence",
                        "score": len(inputs_to_this) * (1.5 if len(domains_involved) >= 3 else 1.0),
                    })

    return sorted(results, key=lambda x: x["score"], reverse=True)


def discover_cross_domain_convergences() -> List[Dict]:
    """
    自动发现所有跨领域汇聚模式。

    返回: [{output_var, converging_laws, domains, score}]
    """
    template = {
        "pattern": "convergence",
        "input_count": 2,
        "output_count": 1,
        "domains": ["mechanics"],  # 已发现的域, 在新域中搜索
    }
    return search_similar_patterns(template, min_inputs=2)


def meta_learning_report() -> str:
    """元学习报告: 发现可迁移的模式"""
    patterns = discover_cross_domain_convergences()

    lines = ["=== 元学习: 跨域汇聚模式 ==="]
    if not patterns:
        lines.append("  未发现新的跨域汇聚模式")
        return "\n".join(lines)

    lines.append(f"  发现 {len(patterns)} 个跨域汇聚:")
    for i, p in enumerate(patterns[:5]):
        lines.append(f"  {i+1}. {p['output_var']} ({p['converging_laws']} 条定律汇聚)")
        lines.append(f"     领域: {p['domains']}")
    return "\n".join(lines)
