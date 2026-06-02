"""
Jaynes 最大熵原理 — 为什么物理分布长这样

E.T. Jaynes (1957):
  "在满足已知约束的所有概率分布中,
   使熵最大的那个分布是最不偏颇的。"

  这是连接概率论和物理学的桥梁:
    - 为什么气体分子的速度分布是 Maxwell-Boltzmann?
      因为它是给定平均能量约束下熵最大的分布。

    - 为什么测量误差是正态分布?
      因为它是给定均值和方差约束下熵最大的分布。

在 PhysCausal 中的应用:
  当数据不足时, 用最大熵原理生成「最不偏颇」的先验分布。
"""

from __future__ import annotations
from typing import Callable, Dict, List, Optional, Tuple
import numpy as np


class MaxEnt:
    """最大熵分布求解器"""

    @staticmethod
    def maxent_distribution(constraints: List[Callable[[np.ndarray], float]],
                            constraint_values: List[float],
                            n_points: int = 100,
                            support: Tuple[float, float] = (-5, 5),
                            n_iterations: int = 500,
                            learning_rate: float = 0.01) -> np.ndarray:
        """
        求满足约束的最大熵分布。

        Args:
            constraints: 约束函数列表 [g₁(x), g₂(x), ...]
            constraint_values: 约束期望值 [E[g₁], E[g₂], ...]
            n_points: 离散化点数
            support: 定义域
            n_iterations: 优化迭代次数
            learning_rate: 学习率

        Returns:
            概率分布 p(x) on support

        原理:
          在约束 E[f_i(x)] = c_i 下,
          最大熵分布形式为:
            p(x) ∝ exp(-Σ λ_i f_i(x))
        """
        x = np.linspace(support[0], support[1], n_points)
        dx = x[1] - x[0]

        # 优化 Lagrange 乘子 λ (从 0 开始)
        n_constraints = len(constraints)
        lambdas = np.zeros(n_constraints)

        for _ in range(n_iterations):
            # 计算未归一化分布
            log_p = np.zeros(n_points)
            for i in range(n_constraints):
                log_p -= lambdas[i] * constraints[i](x)
            log_p -= log_p.max()  # 数值稳定性
            p = np.exp(log_p)
            p = p / (p.sum() * dx)

            # 检查约束
            for i in range(n_constraints):
                expected = np.sum(p * constraints[i](x)) * dx
                error = expected - constraint_values[i]
                lambdas[i] += learning_rate * error

        # 最终归一化
        log_p = np.zeros(n_points)
        for i in range(n_constraints):
            log_p -= lambdas[i] * constraints[i](x)

        # Boltzmann 形式: p(x) ∝ exp(-βH(x))
        # λ_i = β · (系数)
        log_p -= log_p.max()
        p = np.exp(log_p)
        p = p / (p.sum() * dx)

        return p

    @staticmethod
    def gaussian_moment_constraints(data: np.ndarray) -> Tuple:
        """
        从数据中提取矩约束。

        如果只有均值和方差约束 → 最大熵 = 正态分布。
        """
        mu = float(np.mean(data))
        sigma2 = float(np.var(data))

        def mean_constraint(x):
            return x

        def variance_constraint(x):
            return (x - mu) ** 2

        return (
            [mean_constraint, variance_constraint],
            [mu, sigma2],
        )

    @staticmethod
    def physical_boltzmann(energy_func: Callable[[np.ndarray], float],
                           beta: float = 1.0,
                           n_points: int = 200,
                           support: Tuple[float, float] = (-5, 5)) -> np.ndarray:
        """
        Boltzmann 分布: p(x) ∝ exp(-β H(x))

        这是热力学平衡态的分布形式。

        Args:
            energy_func: 能量函数 H(x)
            beta: 逆温度 1/(kT)
        """
        x = np.linspace(support[0], support[1], n_points)
        dx = x[1] - x[0]

        log_p = -beta * energy_func(x)
        log_p -= log_p.max()
        p = np.exp(log_p)
        p = p / (p.sum() * dx)

        return p

    @staticmethod
    def entropy_of_distribution(p: np.ndarray, dx: float = 1.0) -> float:
        """计算分布的熵"""
        p = np.asarray(p)
        p = p[p > 0]
        return float(-np.sum(p * np.log(p)) * dx)

    @staticmethod
    def kl_from_uniform(p: np.ndarray) -> float:
        """KL(P||Uniform) — 分布的「结构化程度」"""
        n = len(p)
        uniform = np.ones(n) / n
        return ShannonEntropy.kl_divergence(p, uniform)


# Import at module level for the static method
from information.shannon import ShannonEntropy
