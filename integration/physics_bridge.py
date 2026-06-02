"""
物理→因果桥接 — 物理约束施加到因果图

数据流:
  因果图 (edges) + 变量名
    → 物理定律库扫描: 匹配相关定律
    → 强制/禁止边: 根据物理定律修改因果图
    → 方程替换: 物理公式替换 SCM 统计拟合方程
    → 输出: 物理约束下的因果图 + SCM
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple

from physics.laws import PhysicsLibrary, library, PhysicsLaw, ConstraintType
from physics.constraints import PhysicsConstrainedDAG


class PhysicsToCausal:
    """
    物理→因果桥接器。

    将物理定律作为先验约束施加到因果发现结果上。
    """

    def __init__(self, physics_lib: Optional[PhysicsLibrary] = None):
        self.lib = physics_lib or library

    def constrain_graph(self,
                        edges: List[Tuple[str, str]],
                        variable_names: List[str],
                        domain: Optional[str] = None) -> Dict:
        """
        对因果图施加物理约束。

        Args:
            edges: 因果边列表 (来自 PC/FCI/GES)
            variable_names: 变量名列表
            domain: 物理领域 (可选, 如 "mechanics")

        Returns:
            {
                "original_edges": [...],
                "constrained_edges": [...],
                "forced_added": [...],      # 物理强制添加的边
                "forbidden_removed": [...],  # 物理禁止而删除的边
                "physics_laws_applied": [...],
                "physics_equations": {...},  # 变量 → 物理公式
            }
        """
        constrained = PhysicsConstrainedDAG(variable_names, self.lib)

        if domain:
            relevant = self.lib.list_by_domain(domain)
        else:
            relevant = self.lib.find_relevant(variable_names)

        original = set(edges)
        constrained_set = set(constrained.apply_to_edges(edges))

        forced_added = constrained_set - original
        forbidden_removed = original - constrained_set

        return {
            "original_edges": list(original),
            "constrained_edges": list(constrained_set),
            "forced_added": list(forced_added),
            "forbidden_removed": list(forbidden_removed),
            "physics_laws_applied": [law.name for law in relevant],
            "physics_equations": constrained.physics_equations,
        }

    def validate_causal_path(self,
                             path: List[str],
                             variable_names: List[str]) -> Dict:
        """
        验证一条因果路径是否物理上可行。

        检查路径中的每条边是否与物理定律冲突。
        """
        edges = [(path[i], path[i+1]) for i in range(len(path)-1)]
        result = self.constrain_graph(edges, variable_names)

        violations = []
        for src, dst in result["forbidden_removed"]:
            violations.append(f"{src}→{dst}: 违反物理定律")

        return {
            "path": path,
            "is_physically_valid": len(violations) == 0,
            "violations": violations,
            "remaining_edges": result["constrained_edges"],
        }

    def suggest_causal_variables(self,
                                  variable_names: List[str]) -> Dict:
        """
        给定变量名列表, 建议可能的因果变量。

        基于物理定律库, 推断哪些变量之间可能存在因果联系。
        """
        relevant = self.lib.find_relevant(variable_names)
        suggestions = []

        for law in relevant:
            for src, dst in law.causal_direction:
                if src in variable_names and dst in variable_names:
                    suggestions.append({
                        "edge": f"{src}→{dst}",
                        "law": law.name,
                        "equation": law.latex,
                        "type": law.constraint_type.name,
                    })

        return {
            "variable_names": variable_names,
            "suggested_edges": suggestions,
            "relevant_laws": [law.name for law in relevant],
        }
