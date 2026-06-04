"""
完整四层流水线 — 端到端 感知→因果结论

PhysCausal Pipeline:
  1. 感知层:  raw data → semantic variables
  2. 谱分解:  PCA → ranked variables
  3. 物理层:  physics constraints → refined DAG
  4. 因果层:  discovery → identification → estimation → counterfactual
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from perception.encoder import SimpleFeatureExtractor
from integration.perception_bridge import PerceptionToCausal, VariableSelector
from integration.physics_bridge import PhysicsToCausal
from integration.information_gate import InformationGate
from spectral.spectral import SpectralDecomposer


class PhysCausalPipeline:
    """
    PhysCausal 完整流水线。

    端到端: 原始数据 → 因果结论
    """

    def __init__(self, beta: float = 0.5):
        self.perception_bridge = PerceptionToCausal()
        self.physics_bridge = PhysicsToCausal()
        self.info_gate = InformationGate(beta=beta)

    def run(self,
            raw_data: np.ndarray,
            variable_names: Optional[List[str]] = None,
            treatment: Optional[str] = None,
            outcome: Optional[str] = None,
            domain: Optional[str] = None,
            verbose: bool = True) -> Dict:
        """
        运行完整流水线。

        Args:
            raw_data: (n_samples × n_features) 数据矩阵
            variable_names: 变量名列表
            treatment: 处理变量 (用于因果效应识别)
            outcome: 结果变量
            domain: 物理领域 ("mechanics" / "electromagnetism" / ...)
            verbose: 是否打印步骤

        Returns:
            {
                "stage": "complete",
                "perception": {...},    # 感知+谱分解结果
                "physics": {...},      # 物理约束结果
                "causal": {...},       # 因果发现+识别+估计结果
            }
        """
        stages = {}

        # ═══ Stage 1: 感知 + 谱分解 ═══
        if verbose:
            print("=== Stage 1: Perception + Spectral ===")

        if variable_names is None:
            variable_names = [f"V{i}" for i in range(raw_data.shape[1])]

        perception_result = self.perception_bridge.process(
            raw_data, variable_names, verbose=verbose
        )
        stages["perception"] = perception_result

        selected_vars = perception_result["variable_names"]
        selected_data = perception_result["data"]

        # ═══ Stage 1.5: 信息质检 ═══
        n_orig = raw_data.shape[1]
        n_comp = selected_data.shape[1]
        if verbose:
            print(f"\n  Information Gate: {n_orig}dim → {n_comp}dim")

        target_data = None
        if outcome and outcome in variable_names:
            t_idx = variable_names.index(outcome)
            target_data = raw_data[:, t_idx]

        info_result = self.info_gate.measure_compression(
            raw_data, selected_data, target_data,
            step_name=f"perception_{n_orig}d_to_{n_comp}d"
        )
        stages["information"] = info_result

        if verbose:
            print(f"    I(T;Y) retained: {info_result['i_ty']:.1%}  "
                  f"{info_result['verdict']}")

        if info_result["verdict"] == "warning" and n_comp > 3:
            if verbose:
                print("    ⚠ High info loss, keeping more dimensions...")
            # 回退: 保留更多维度
            selected_vars = variable_names[:max(n_comp + 2, n_orig // 2)]
            selected_data = raw_data[:, :len(selected_vars)]

        # ═══ Stage 2: 因果发现 ═══
        if verbose:
            print(f"\n=== Stage 2: Causal Discovery ===")

        causal_result = self._causal_discovery(selected_data, selected_vars, verbose)
        stages["causal"] = causal_result

        # ═══ Stage 3: 物理约束 ═══
        if verbose:
            print(f"\n=== Stage 3: Physics Constraints ===")

        if causal_result.get("edges"):
            physics_result = self.physics_bridge.constrain_graph(
                causal_result["edges"],
                selected_vars,
                domain=domain,
            )
            stages["physics"] = physics_result

            if verbose:
                print(f"  Original edges: {len(physics_result['original_edges'])}")
                print(f"  Constrained edges: {len(physics_result['constrained_edges'])}")
                if physics_result["forced_added"]:
                    print(f"  Forced added: {physics_result['forced_added']}")
                if physics_result["forbidden_removed"]:
                    print(f"  Forbidden removed: {physics_result['forbidden_removed']}")

            # 使用约束后的边更新因果层
            causal_result["constrained_edges"] = physics_result["constrained_edges"]

        # ═══ Stage 4: 识别 + 估计 ═══
        if treatment and outcome and causal_result.get("edges"):
            if verbose:
                print(f"\n=== Stage 4: Identification + Estimation ===")
                print(f"  Treatment: {treatment}, Outcome: {outcome}")

            ident_result = self._identify_and_estimate(
                selected_data, selected_vars,
                treatment, outcome,
                causal_result.get("constrained_edges", causal_result["edges"]),
                verbose,
            )
            stages["inference"] = ident_result

        stages["stage"] = "complete"
        return stages

    def _causal_discovery(self, data, var_names, verbose):
        """因果发现 (PC 算法)"""
        try:
            from causal.discovery import pc_algorithm
            from causal.graph import CausalDAG

            dag = pc_algorithm(data, var_names, alpha=0.05)
            edges_list = [(src, dst) for src in var_names for dst in dag.children(src)]

            if verbose:
                print(f"  Variables: {len(var_names)}")
                print(f"  Discovered edges: {len(edges_list)}")
                if edges_list:
                    for s, d in edges_list[:10]:
                        print(f"    {s} → {d}")

            return {
                "edges": edges_list,
                "dag": dag,
                "n_variables": len(var_names),
                "n_edges": len(edges_list),
            }
        except Exception as e:
            if verbose:
                print(f"  Discovery failed: {e}")
            return {"edges": [], "error": str(e)}

    def _identify_and_estimate(self, data, var_names, treatment, outcome,
                                edges, verbose):
        """识别 + 估计"""
        try:
            from causal.graph import CausalDAG
            from causal.identification import identify_effect
            from causal.estimation import estimate_effect

            dag = CausalDAG(var_names, edges)
            ident = identify_effect(dag, treatment, outcome)

            if not ident.identifiable:
                return {
                    "identifiable": False,
                    "reason": ident.reason if hasattr(ident, 'reason') else "unknown",
                }

            adj_set = ident.adjustment_set
            est = estimate_effect(data, var_names, treatment, outcome,
                                  list(adj_set) if adj_set else [], "auto")

            result = {
                "identifiable": True,
                "method": ident.method,
                "adjustment_set": list(adj_set) if adj_set else [],
                "ate": float(est.ate) if hasattr(est, 'ate') else None,
                "std_error": float(est.std_error) if hasattr(est, 'std_error') else None,
            }

            if hasattr(est, 'ci_lower') and hasattr(est, 'ci_upper'):
                result["ci"] = (float(est.ci_lower), float(est.ci_upper))

            if verbose:
                print(f"  Method: {ident.method}")
                print(f"  Adjustment: {result['adjustment_set']}")
                print(f"  ATE: {result['ate']}")
                if 'ci' in result:
                    print(f"  95% CI: [{result['ci'][0]:.4f}, {result['ci'][1]:.4f}]")

            return result
        except Exception as e:
            if verbose:
                print(f"  Identification failed: {e}")
            return {"identifiable": False, "error": str(e)}

    def quick_analyze(self,
                      raw_data: np.ndarray,
                      variable_names: List[str],
                      treatment: str,
                      outcome: str) -> str:
        """
        快速分析 — 一行调用, 返回人类可读的摘要。
        """
        result = self.run(
            raw_data, variable_names,
            treatment=treatment, outcome=outcome,
            verbose=False,
        )

        lines = ["=" * 50]
        lines.append("PhysCausal Quick Analysis")
        lines.append("=" * 50)

        perc = result.get("perception", {})
        lines.append(f"\nPerception: {perc.get('n_selected', '?')} variables selected "
                     f"from {perc.get('n_original', '?')} "
                     f"({perc.get('explained_variance', 0):.0%} variance)")

        causal = result.get("causal", {})
        lines.append(f"Causal: {causal.get('n_edges', 0)} edges discovered")

        inference = result.get("inference", {})
        if inference.get("identifiable"):
            lines.append(f"\nEffect: {inference['method']}")
            lines.append(f"  ATE = {inference['ate']:.4f} ± {inference['std_error']:.4f}")
            if "ci" in inference:
                lines.append(f"  95% CI: [{inference['ci'][0]:.4f}, {inference['ci'][1]:.4f}]")
        else:
            lines.append(f"\nEffect: not identifiable")

        return "\n".join(lines)
