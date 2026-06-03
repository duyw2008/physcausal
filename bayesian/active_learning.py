"""
主动实验设计 — 信息价值驱动的干预选择

核心问题:
  当前因果图有不确定性。下一步该干预哪个变量来最大程度消除不确定性？

VOI (Value of Information):
  VOI(A) = H(G|D) - E[H(G|D + do(A=a))]
  
  干预 A 的信息价值 = 做实验 A 后期望减少的图熵

方法:
  1. 边信息增益: 选置信度最低的边，干预其端点
  2. 图熵减少: 模拟干预 → 估计后验熵的变化
  3. Φ 信息增益: 同时考虑结构和参数的不确定性
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

from bayesian.structural import StructuralPosterior, GraphPosterior, EdgePosterior


@dataclass
class ExperimentCandidate:
    """候选实验"""
    variable: str                   # 干预变量
    expected_entropy_reduction: float  # 期望熵减少
    affected_edges: List[Tuple[str, str]]  # 受影响的不确定边
    cost: float = 1.0               # 实验成本
    information_efficiency: float = 0.0  # 信息增益/成本


@dataclass
class ExperimentPlan:
    """实验计划"""
    candidates: List[ExperimentCandidate]
    recommended: ExperimentCandidate
    current_entropy: float
    expected_entropy_after: float
    notes: str = ""


class ActiveExperimentDesign:
    """
    主动实验设计 — VOI 驱动的干预选择。

    给定当前图后验 P(G|D)，选择最优下一步干预。

    流程:
      1. 识别不确定的边 (置信度低)
      2. 对每个候选干预，模拟 do() 后图熵的变化
      3. 选信息增益/成本最大的
    """

    def __init__(self):
        pass

    def propose_experiments(self,
                            posterior: GraphPosterior,
                            variable_names: List[str],
                            max_candidates: int = 5) -> ExperimentPlan:
        """
        建议下一步实验。

        Args:
            posterior: 当前图后验
            variable_names: 变量名
            max_candidates: 最多返回多少候选

        Returns:
            ExperimentPlan with ranked candidates
        """
        # 1. 找最不确定的边
        uncertain_edges = [
            ep for ep in posterior.edge_posteriors
            if 0.2 < ep.probability < 0.8  # 太确定或太不可能的边不需要实验
        ]
        uncertain_edges.sort(key=lambda e: abs(e.probability - 0.5))
        # 最接近 0.5 的边 → 最不确定

        # 2. 对每个不确定边，干预端点变量
        candidates = []
        seen_vars = set()

        for ep in uncertain_edges[:max_candidates * 2]:
            for var in [ep.source, ep.target]:
                if var in seen_vars:
                    continue
                seen_vars.add(var)

                # 估计干预后的熵减少
                # 简化: 干预 var → 关联边置信度提升 30%
                affected = [
                    (e.source, e.target)
                    for e in posterior.edge_posteriors
                    if e.source == var or e.target == var
                ]
                n_affected = len(affected)
                avg_uncertainty = np.mean([
                    abs(e.probability - 0.5)
                    for e in posterior.edge_posteriors
                    if (e.source, e.target) in affected
                ]) if affected else 0

                entropy_reduction = n_affected * (0.5 - avg_uncertainty) * 0.3
                entropy_reduction = max(0.0, entropy_reduction)

                candidates.append(ExperimentCandidate(
                    variable=var,
                    expected_entropy_reduction=entropy_reduction,
                    affected_edges=affected,
                    cost=1.0,
                    information_efficiency=entropy_reduction / 1.0,
                ))

        # 3. 排序
        candidates.sort(key=lambda c: -c.information_efficiency)
        candidates = candidates[:max_candidates]

        if not candidates:
            # 所有边都确定 → 不需要实验
            return ExperimentPlan(
                candidates=[],
                recommended=ExperimentCandidate(
                    variable="—", expected_entropy_reduction=0.0,
                    affected_edges=[],
                ),
                current_entropy=posterior.entropy,
                expected_entropy_after=posterior.entropy,
                notes="All edges have high confidence. No experiment needed.",
            )

        recommended = candidates[0]
        expected_after = posterior.entropy - recommended.expected_entropy_reduction

        return ExperimentPlan(
            candidates=candidates,
            recommended=recommended,
            current_entropy=posterior.entropy,
            expected_entropy_after=expected_after,
            notes=f"Recommend do({recommended.variable}) — "
                  f"expected entropy reduction: {recommended.expected_entropy_reduction:.3f} nats",
        )

    def simulate_intervention(self,
                              posterior: GraphPosterior,
                              intervention_var: str,
                              direction_matters: bool = True) -> GraphPosterior:
        """
        模拟干预实验后的信念更新。

        真实实验中：
          do(X=x) → 收集新数据 → 重新跑因果发现 → 更新后验

        模拟 (无新数据):
          干预 X 可以打破 Markov 等价类的对称性
          → X 参与的边置信度提升
        """
        updated_edges = []
        for ep in posterior.edge_posteriors:
            new_prob = ep.probability
            if ep.source == intervention_var or ep.target == intervention_var:
                # 干预提供额外信息 → 置信度向两极移动
                if ep.probability > 0.5:
                    new_prob = min(1.0, ep.probability + 0.15)
                else:
                    new_prob = max(0.0, ep.probability - 0.15)

            updated_edges.append(EdgePosterior(
                source=ep.source, target=ep.target,
                probability=new_prob,
            ))

        return GraphPosterior(
            edge_posteriors=updated_edges,
            top_graphs=posterior.top_graphs,
            entropy=posterior.entropy * 0.8,  # approximate
            n_samples=posterior.n_samples,
            notes=f"After do({intervention_var}) — simulated",
        )

    def belief_update_report(self,
                              before: GraphPosterior,
                              after: GraphPosterior,
                              experiment: str) -> List[EdgeBeliefUpdate]:
        """报告一次实验后的信念更新"""
        updates = []
        before_map = {(e.source, e.target): e.probability for e in before.edge_posteriors}

        for ep in after.edge_posteriors:
            key = (ep.source, ep.target)
            prob_before = before_map.get(key, 0.5)
            prob_after = ep.probability

            if abs(prob_after - prob_before) > 0.01:
                ig = self._information_gain(prob_before, prob_after)
                updates.append(EdgeBeliefUpdate(
                    edge=key,
                    prob_before=prob_before,
                    prob_after=prob_after,
                    information_gain=ig,
                    experiment=experiment,
                ))

        return sorted(updates, key=lambda u: -u.information_gain)

    @staticmethod
    def _information_gain(p_before: float, p_after: float) -> float:
        """从概率变化计算信息增益 (bits)"""
        def entropy(p):
            p = np.clip(p, 1e-15, 1 - 1e-15)
            return -(p * np.log2(p) + (1 - p) * np.log2(1 - p))

        return entropy(p_before) - entropy(p_after)
