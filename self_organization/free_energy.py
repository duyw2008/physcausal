"""
自组织 — 自由能原理 + 主动推理

三部曲的第三章:
  对称 (元原则)  →  破缺 (物理)  →  自组织 (自由能)

核心:
  自由能 = 预测误差 + 模型复杂度
  智能体的内在驱动力: 最小化自由能
  → 主动干预世界来减少不确定性
  → 自发保持在学习 (探索) 与利用 (执行) 的临界点

与 VOI 的关系:
  VOI = 干预 A 能减少多少不确定性的期望
  自由能 = 智能体在任何时刻都应该最小化的量
  VOI 是单步的，自由能是持续的驱动力

公式:
  F = E_q[log q(s) - log p(o,s|a)]
    ≈ 预测误差 + KL(q(s)||p(s))
  
  期望自由能 G(π):
    = E[log q(s|π) - log q(s|o,π)]  (信息增益, 促进探索)
    + E[log p(o|C)]                  (偏好满足, 促进利用)

PhysCausal 特化:
  s = 因果图 G
  o = 观测数据 D
  a = 干预 do(X=x)
  F ≈ -BIC + H(G|D)
  G(干预) ≈ VOI(干预) + 目标匹配度
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np


class FreeEnergyAgent:
    """
    自由能驱动的自组织智能体。

    三个核心概念:
      1. 信念更新: P(G|D) — 贝叶斯推断
      2. 行动选择: argmin G(π) — 最小化期望自由能
      3. 临界自调节: β 参数 — 探索/利用平衡
    """

    def __init__(self, beta: float = 1.0):
        """
        Args:
            beta: 探索-利用权衡参数
                  beta > 1: 偏好探索 (信息增益驱动)
                  beta < 1: 偏好利用 (目标驱动)
                  beta ≈ 1: 临界点 (自适应平衡)
        """
        self.beta = beta
        self.free_energy_history: List[float] = []
        self._action_values: Dict[str, float] = {}
        self.adaptive_beta = True  # 自适应调节

    def variational_free_energy(self,
                                 posterior_entropy: float,
                                 bic_score: float) -> float:
        """
        变分自由能。

        F = 复杂度 - 准确度
          = -BIC + H(G|D)

        越低越好:
          准确的模型 (高似然=BIC绝对值大) → F ↓
          确定的信念 (低后验熵) → F ↓
        """
        return -bic_score + posterior_entropy

    def expected_free_energy(self,
                              information_gain: float,
                              goal_alignment: float) -> float:
        """
        期望自由能 G(π) — 用于选择行动。

        G = β · (信息增益) + (1-β) · (1-目标匹配度)

        β 大: 偏好探索 — 选信息增益大的行动
        β 小: 偏好利用 — 选目标匹配度高的行动
        """
        return self.beta * information_gain + (1 - self.beta) * (1 - goal_alignment)

    def select_action(self,
                       candidates: List[Dict],
                       current_goals: Optional[List[str]] = None) -> Dict:
        """
        选择最优行动。

        Args:
            candidates: [{"variable": ..., "voi": ..., "goal_alignment": ...}, ...]
            current_goals: 当前目标变量列表

        Returns:
            最优候选
        """
        if not candidates:
            return {"variable": "none", "expected_free_energy": float("inf")}

        for c in candidates:
            c["expected_free_energy"] = self.expected_free_energy(
                c.get("voi", 0.0),
                c.get("goal_alignment", 0.0),
            )

        # 按期望自由能升序 (越小越好)
        candidates.sort(key=lambda c: c["expected_free_energy"])
        return candidates[0]

    def update_beta(self, recent_accuracy: List[float]):
        """
        自适应调节 β — 保持在临界点。

        当准确率高时 → β ↑ (更多探索, 防止过拟合)
        当准确率低时 → β ↓ (更多利用, 优先改进已有的)
        当准确率波动时 → β → 1 (保持临界)
        """
        if not self.adaptive_beta or len(recent_accuracy) < 3:
            return

        # 准确率变化趋势
        trend = np.mean(np.diff(recent_accuracy[-5:]))

        if trend > 0.05:  # 在进步 → 稍微多探索
            self.beta = min(2.0, self.beta * 1.1)
        elif trend < -0.05:  # 在退步 → 利用已知
            self.beta = max(0.1, self.beta * 0.9)
        else:  # 稳定 → 回到临界附近
            self.beta = 0.5 * self.beta + 0.5  # 渐进回 1.0

    def status(self) -> Dict:
        return {
            "beta": round(self.beta, 3),
            "mode": "explore" if self.beta > 1.1 else (
                "exploit" if self.beta < 0.9 else "critical"
            ),
            "n_steps": len(self.free_energy_history),
            "avg_free_energy": (
                np.mean(self.free_energy_history[-10:])
                if self.free_energy_history else float("nan")
            ),
        }


class SelfOrganizingLearner:
    """
    自组织学习器 — 整合 FreeEnergyAgent + ActiveLearner。

    循环:
      1. 评估当前自由能 F
      2. 选行动: argmin G(π)
      3. 执行干预 → 收集数据
      4. 更新信念 P(G|D)
      5. 自适应 β
      6. 重复 → 自发保持在学习/利用临界点
    """

    def __init__(self, env):
        from bayesian.structural import StructuralPosterior
        from active_experiment.active_learner import ActiveLearner

        self.env = env
        self.learner = ActiveLearner(env)
        self.agent = FreeEnergyAgent()
        self.structural = StructuralPosterior()
        self.accuracy_history: List[float] = []

    def step(self, goals: Optional[List[str]] = None) -> Dict:
        """
        一步自组织: 评估 → 选行动 → 执行 → 更新。

        Args:
            goals: 目标变量 (如果不给, 纯探索)

        Returns:
            {action, free_energy, beta, accuracy, ...}
        """
        env_info = self.env.variable_info()
        variables = env_info["variables"]

        # 1. 评估当前状态
        if self.learner.posterior:
            posterior = self.learner.posterior
            fe = self.agent.variational_free_energy(
                posterior.entropy,
                -100,  # BIC 近似 (使用现有的)
            )
            self.agent.free_energy_history.append(fe)

            # 候选行动 — 每个可干预的变量
            candidates = []
            for var in variables:
                if var not in [e[1] for e in env_info["ground_truth"]] + ["v1p", "v2p"]:
                    # 只能干预原因变量
                    voi = 0.5  # 简化: 均匀信息增益
                    goal_align = 1.0 if (goals and var in goals) else 0.3
                    candidates.append({
                        "variable": var, "voi": voi, "goal_alignment": goal_align,
                    })

            # 2. 选行动
            action = self.agent.select_action(candidates)
        else:
            # 首次: 随机选一个可干预变量
            non_outcome = [v for v in variables 
                          if v not in [e[1] for e in env_info["ground_truth"]]]
            action = {"variable": np.random.choice(non_outcome) if non_outcome else variables[0]}

        # 3. 执行
        experiment_var = action.get("variable", variables[0])
        value = np.random.uniform(0.5, 2.0)
        new_data = self.env.experiment({experiment_var: value}, n_samples=30)
        self.learner.data_history.append(new_data)
        self.learner.total_samples += len(new_data)

        # 4. 更新信念
        all_data = np.vstack(self.learner.data_history)
        phys_edges = self.learner._physics_prior(variables)
        if phys_edges:
            posterior = self.structural.infer_from_edges(phys_edges, variables, all_data)
        else:
            posterior = self.structural.infer(all_data, variables, n_samples=5)
        self.learner.posterior = posterior

        # 5. 自适应 β
        true_edges = set(tuple(e) for e in env_info["ground_truth"])
        discovered = set()
        for ep in posterior.edge_posteriors:
            if ep.probability > 0.5:
                discovered.add((ep.source, ep.target))
        accuracy = len(discovered & true_edges) / max(len(true_edges), 1)
        self.accuracy_history.append(accuracy)
        self.agent.update_beta(self.accuracy_history)

        return {
            "action": experiment_var,
            "action_value": value,
            "free_energy": (
                self.agent.free_energy_history[-1]
                if self.agent.free_energy_history else None
            ),
            "beta": self.agent.beta,
            "accuracy": accuracy,
            "mode": self.agent.status()["mode"],
        }

    def run(self, n_steps: int = 10, goals: Optional[List[str]] = None,
            verbose: bool = True) -> Dict:
        """运行自组织循环"""
        history = []
        for i in range(n_steps):
            result = self.step(goals)
            history.append(result)
            if verbose and i % 3 == 0:
                print(f"  Step {i}: do({result['action']}) → "
                      f"β={result['beta']:.2f}({result['mode']}) "
                      f"acc={result['accuracy']:.0%}")

        return {
            "steps": n_steps,
            "history": history,
            "final_accuracy": history[-1]["accuracy"],
            "final_mode": history[-1]["mode"],
            "beta_trajectory": self.agent.status(),
        }
