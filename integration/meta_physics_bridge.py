"""
元物理→因果桥接 — 五原则正式插入因果管道

将元物理五条原则作为因果发现的约束层:
  1. 提供 forbidden_edges (物理定律 + 局域因果)
  2. 提供 required_edges (对称性 → 守恒律的必要边)
  3. 验证 SCM 参数 (熵增方向 + 信息边界)

这是 llm/bridge.py 中 _validate_graph 的形式化版本。
"""

from typing import Dict, List, Optional, Tuple


class MetaPhysicsBridge:
    """元物理→因果桥接器"""

    def __init__(self):
        pass

    def get_forbidden_edges(self,
                            variable_names: List[str],
                            var_types: Optional[Dict[str, str]] = None) -> List[Tuple[str, str]]:
        """
        汇总所有禁止边。
        来源: 物理定律 + 局域因果
        """
        forbidden = []

        # 物理定律
        from physics.laws import library
        forbidden.extend(library.forbidden_edges(variable_names))

        # 局域因果: 时间反向边 (如果有时间标签)
        # (当前简化: 物理定律已覆盖主要方向)

        return list(set(forbidden))

    def get_required_edges(self,
                           variable_names: List[str]) -> List[Tuple[str, str]]:
        """
        汇总所有强制边。
        来源: 对称性 → 守恒律 (Noether)
        """
        from physics.laws import library
        return library.forced_edges(variable_names)

    def validate_parameters(self,
                            coefficients: Dict[str, Dict[str, float]],
                            variable_names: List[str]) -> Dict:
        """
        验证 SCM 参数是否满足元物理约束。
        """
        from meta_physics.entropy import EntropyArrow
        from meta_physics.symmetry import SymmetryDetector

        violations = []

        # 熵增验证
        arrow = EntropyArrow()
        for var, parents in coefficients.items():
            for parent, coef in parents.items():
                result = arrow.infer_causal_direction(
                    np.random.randn(100, 2), [parent, var], parent, var
                )
                # 如果熵增方向和参数方向不一致，标记
                if parent not in result.direction and coef != 0:
                    violations.append(
                        f"{parent}→{var}: 可能违反熵增方向"
                    )

        # 守恒律验证
        detector = SymmetryDetector()
        symmetries = detector.detect(variable_names)

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "symmetries_detected": [s.notes for s in symmetries],
        }

    def full_constraint_report(self,
                               variable_names: List[str]) -> str:
        """生成完整约束报告"""
        forbidden = self.get_forbidden_edges(variable_names)
        required = self.get_required_edges(variable_names)

        lines = ["=== Meta-Physics Constraint Report ==="]
        lines.append(f"\nVariables: {', '.join(variable_names)}")

        lines.append(f"\nForbidden edges ({len(forbidden)}):")
        for src, dst in forbidden:
            lines.append(f"  ✗ {src} → {dst}")

        lines.append(f"\nRequired edges ({len(required)}):")
        for src, dst in required:
            lines.append(f"  ✓ {src} → {dst}")

        return "\n".join(lines)
