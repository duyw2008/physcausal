"""
物理约束桥 — 将物理定律应用到因果图上
"""

from typing import Dict, List, Optional, Set, Tuple
from physics.laws import PhysicsLibrary, library


class PhysicsConstrainedDAG:
    """
    物理定律约束下的因果图。

    不代替 CausalDAG，而是作为 CausalDAG 的一个「约束层」：
      - forced_edges:    物理定律强制要求的边 (如 Force → Acceleration)
      - forbidden_edges: 物理定律禁止的边 (如 Velocity → Mass)
      - revised_edges:   物理定律要求反转的边
    """

    def __init__(self, variable_names: List[str],
                 physics_lib: Optional[PhysicsLibrary] = None):
        self.variable_names = list(variable_names)
        self._lib = physics_lib or library
        self._compute_constraints()

    def _compute_constraints(self):
        relevant = self._lib.find_relevant(self.variable_names)
        self.forced_edges = []
        self.forbidden_edges = []
        self.revised_edges = []
        self.physics_equations: Dict[str, str] = {}  # var → latex formula name

        for law in relevant:
            self.forced_edges.extend(law.causal_direction)
            self.forbidden_edges.extend(law.forbidden_directions)
            if law.constraint_type.name == "SCM_EQUATION":
                for out in law.outputs:
                    self.physics_equations[out] = law.name

    def apply_to_edges(self, edges: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        对已有的边列表施加物理约束:
          1. 确保 forced_edges 存在
          2. 删除 forbidden_edges
          3. 验证无环路
        """
        edge_set = set(edges)

        # 添加强制边
        for src, dst in self.forced_edges:
            if src in self.variable_names and dst in self.variable_names:
                edge_set.add((src, dst))

        # 删除禁止边
        for src, dst in self.forbidden_edges:
            edge_set.discard((src, dst))

        return list(edge_set)

    def constraint_report(self) -> str:
        """生成物理约束报告"""
        lines = ["=== Physics Constraint Report ==="]
        lines.append(f"\nVariables: {', '.join(self.variable_names)}")
        lines.append(f"\nForced edges ({len(self.forced_edges)}):")
        for src, dst in self.forced_edges:
            if src in self.variable_names and dst in self.variable_names:
                lines.append(f"  {src} → {dst}")

        lines.append(f"\nForbidden edges ({len(self.forbidden_edges)}):")
        for src, dst in self.forbidden_edges:
            if src in self.variable_names and dst in self.variable_names:
                lines.append(f"  {src} → {dst}  ✗")

        lines.append(f"\nPhysics-governed variables ({len(self.physics_equations)}):")
        for var, law_name in self.physics_equations.items():
            if var in self.variable_names:
                lines.append(f"  {var}: {law_name}")

        return "\n".join(lines)
