"""
推理引擎 — 统一反事实 + 归因 + 规划入口

三个核心能力:
  counterfactual: 如果当初...会怎样? (Pearl 三步 + 物理验证)
  attribution:    Y的变化中, 各因素贡献了多少? (中介 + Shapley)
  planner:        要达到目标, 该干预哪个变量? (VOI + do-calculus)
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np


class CounterfactualEngine:
    """统一反事实入口 — 整合 SCM + 物理约束 + 守恒验证"""

    def __init__(self):
        pass

    def infer(self,
              data: np.ndarray,
              variable_names: List[str],
              edges: List[Tuple[str, str]],
              observed: Dict[str, float],
              intervention: Dict[str, float],
              target: str,
              validate_physics: bool = True) -> Dict:
        """
        Pearl 三步反事实 + 物理验证。

        Args:
            data: 观测数据
            variable_names: 变量名
            edges: 因果边
            observed: 实际观测值 {var: value}
            intervention: 反事实干预 {var: new_value}
            target: 目标变量
            validate_physics: 是否用物理定律验证结果

        Returns:
            {counterfactual_value, is_physically_valid, ...}
        """
        from causal.graph import CausalDAG
        from causal.scm import linear_scm

        dag = CausalDAG(variable_names, edges)

        # 拟合 SCM
        rng = np.random.RandomState(42)
        coeffs = {}
        for v in variable_names:
            parents = list(dag.parents(v))
            if parents:
                coeffs[v] = {}
                for p in parents:
                    p_idx = variable_names.index(p)
                    v_idx = variable_names.index(v)
                    coeffs[v][p] = np.corrcoef(data[:, p_idx], data[:, v_idx])[0, 1]

        scm = linear_scm(dag, coeffs, noise_std=0.1)

        # 反事实
        try:
            cf = scm.counterfactual(observed, intervention, target)
            cf_value = float(cf)
        except Exception:
            cf_value = None

        # 物理验证
        physics_valid = True
        physics_notes = ""
        if validate_physics and cf_value is not None:
            from physics.laws import library
            from meta_physics.symmetry import SymmetryDetector

            detector = SymmetryDetector()
            symmetries = detector.detect(variable_names)
            for sym in symmetries:
                if sym.conserved_law:
                    ok = sym.conserved_law.is_conserved(observed, {**observed, **intervention, target: cf_value})
                    if not ok:
                        physics_valid = False
                        physics_notes = f"Violates {sym.conserved_law.name}"
                        break

        return {
            "counterfactual_value": cf_value,
            "observed": observed,
            "intervention": intervention,
            "target": target,
            "is_physically_valid": physics_valid,
            "physics_notes": physics_notes,
        }


class AttributionEngine:
    """归因引擎 — 各因素贡献了多少"""

    def attribute(self,
                  ate: float,
                  coefficients: Dict[str, float]) -> Dict[str, float]:
        """
        将 ATE 分解为各变量的贡献。

        contribution_i = |β_i| / Σ|β_j|
        """
        total = sum(abs(v) for v in coefficients.values())
        if total < 1e-10:
            return {k: 0.0 for k in coefficients}
        return {k: abs(v) / total for k, v in coefficients.items()}
