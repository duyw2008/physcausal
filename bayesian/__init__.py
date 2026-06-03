"""
贝叶斯推断层 (Bayesian) — 不确定性量化 + 主动实验设计

不替代因果层，而是包裹它，提供不确定性视角。

模块:
  structural.py     — P(G|D): 因果图的结构后验 (Bootstrap / MCMC)
  parameter.py      — P(θ|G,D): SCM 参数的后验分布 (共轭先验)
  active_learning.py — VOI: 主动实验选择 (信息价值驱动)

核心哲学:
  从「给我一个答案」→ 「给我答案 + 我对答案的把握 + 如果不确定该做什么」

  贝叶斯网络 vs 贝叶斯推断:
    贝叶斯网络 = 有向图 + 条件概率表 (CausalDAG 已覆盖图结构)
    贝叶斯推断 = P(θ|D) ∝ P(D|θ) P(θ) — 这才是我们要的
"""

from bayesian.structural import (
    EdgePosterior, GraphPosterior, EdgeBeliefUpdate,
    StructuralPosterior,
)
from bayesian.parameter import (
    Posterior, ParameterPosterior, ParameterInference,
)
from bayesian.active_learning import (
    ExperimentCandidate, ExperimentPlan, ActiveExperimentDesign,
)

__all__ = [
    "EdgePosterior", "GraphPosterior", "EdgeBeliefUpdate",
    "StructuralPosterior",
    "Posterior", "ParameterPosterior", "ParameterInference",
    "ExperimentCandidate", "ExperimentPlan", "ActiveExperimentDesign",
]
