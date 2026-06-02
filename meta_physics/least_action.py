"""
最小作用量原理 — 所有动力学的生成性原理

元物理层 Tier 0 — 生成性原理 ①

核心:
  作用量 S[q] = ∫ L(q, q̇, t) dt
  自然界的真实路径满足 δS = 0 (Euler-Lagrange 方程)

在因果推断中的应用:
  1. 因果路径验证: 一条假设的因果链是否物理上可实现?
     → 计算其作用量, 与最小作用量路径比较
  2. 因果路径发现: 在已知起始状态和目标状态时, 真实的因果路径是什么?
     → 变分优化寻找 δS=0 的路径
  3. 反事实验证: 反事实轨迹是否满足最小作用量?
     → 如果不满足, 该反事实在物理上不可能
  4. 对称性桥接: Lagrangian 的对称性 → Noether 守恒律
     → 连接 symmetry.py

与其他元物理模块的关系:
  least_action → symmetry:   L 的对称性 → 守恒量 (Noether)
  least_action → entropy:    不可逆过程 = 含耗散项的 L
  least_action → measurement: 路径积分中每条路径 = 一个可能世界分支
  least_action → spectral:   Koopman 本征函数 = δS=0 路径的谱分解
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
import numpy as np


# ═══════════════════════════════════════════════════════════════
# Core: Lagrangian & Action
# ═══════════════════════════════════════════════════════════════

@dataclass
class Lagrangian:
    """
    拉格朗日量 L(q, q̇, t) — 系统的完整动力学描述。

    L = T - V  (动能 - 势能)

    系统的一切动力学行为完全由 L 决定。
    这包括: 运动方程、守恒律、对称性、相空间结构。
    """
    name: str
    kinetic: Callable[..., float]    # T(q̇, ...)
    potential: Callable[..., float]  # V(q, ...)
    variables: List[str]              # 广义坐标名
    parameters: Dict[str, float] = field(default_factory=dict)

    def __call__(self, q: float, q_dot: float, **kwargs) -> float:
        """L(q, q̇) = T - V"""
        return self.kinetic(q_dot, **kwargs) - self.potential(q, **kwargs)


@dataclass
class ActionResult:
    """变分验证结果"""
    action: float                    # 路径的作用量
    is_stationary: bool              # 是否满足 δS=0 (在容差内)
    max_gradient: float              # max |δS/δq| — 偏离稳态的程度
    euler_lagrange_residual: float   # EL 方程的残差
    path: np.ndarray                 # 路径 q(t)
    notes: str = ""


# ═══════════════════════════════════════════════════════════════
# Pre-built Lagrangian templates
# ═══════════════════════════════════════════════════════════════

def simple_pendulum(length: float = 1.0, g: float = 9.81) -> Lagrangian:
    """单摆: L = ½ml²θ̇² - mgl(1-cosθ)"""
    return Lagrangian(
        name="Simple Pendulum",
        kinetic=lambda q_dot, mass=1.0, length=1.0, **kw: 0.5 * mass * length * length * q_dot * q_dot,
        potential=lambda q, mass=1.0, length=1.0, g=9.81, **kw: mass * g * length * (1 - np.cos(q)),
        variables=["theta"],
        parameters={"mass": 1.0, "length": length, "g": g},
    )


def harmonic_oscillator(omega: float = 1.0) -> Lagrangian:
    """谐振子: L = ½mq̇² - ½kq²"""
    return Lagrangian(
        name="Harmonic Oscillator",
        kinetic=lambda q_dot, mass=1.0, **kw: 0.5 * mass * q_dot * q_dot,
        potential=lambda q, mass=1.0, k=None, **kw: 0.5 * (k if k else omega*omega) * q * q,
        variables=["x"],
        parameters={"mass": 1.0, "k": omega * omega},
    )


def free_particle() -> Lagrangian:
    """自由粒子: L = ½mq̇²"""
    return Lagrangian(
        name="Free Particle",
        kinetic=lambda q_dot, mass=1.0, **kw: 0.5 * mass * q_dot * q_dot,
        potential=lambda q, **kw: 0.0,
        variables=["x"],
        parameters={"mass": 1.0},
    )


def kepler_system(GM: float = 1.0) -> Lagrangian:
    """开普勒问题: L = ½m(ṙ² + r²θ̇²) + GMm/r"""
    # 简化: 仅径向坐标
    return Lagrangian(
        name="Kepler (radial)",
        kinetic=lambda r_dot, mass=1.0, **kw: 0.5 * mass * r_dot * r_dot,
        potential=lambda r, mass=1.0, GM=1.0, **kw: -GM * mass / (abs(r) + 1e-10),
        variables=["r"],
        parameters={"mass": 1.0, "GM": GM},
    )


# ═══════════════════════════════════════════════════════════════
# Action Principle Engine
# ═══════════════════════════════════════════════════════════════

class ActionPrinciple:
    """
    作用量原理引擎。

    核心操作:
      1. compute_action(q_path, dt) → S[q] = ∫ L dt
      2. validate_path(q_path, dt)  → 是否满足 δS=0
      3. find_stationary_path(q0, qT, n_steps) → 变分优化
      4. euler_lagrange_check(q_path, dt) → EL 方程残差
    """

    def __init__(self, lagrangian: Lagrangian, tolerance: float = 0.02):
        self.L = lagrangian
        self.tolerance = tolerance

    def compute_action(self, q_path: np.ndarray, dt: float) -> float:
        """
        计算路径的作用量。

        S[q] = ∫₀ᵀ L(q, q̇) dt
             ≈ Σᵢ L(qᵢ, (qᵢ₊₁ - qᵢ)/dt) · dt
        """
        S = 0.0
        for i in range(len(q_path) - 1):
            q = q_path[i]
            q_dot = (q_path[i + 1] - q_path[i]) / dt
            S += self.L(q, q_dot, **self.L.parameters) * dt
        return float(S)

    def validate_path(self, q_path: np.ndarray, dt: float) -> ActionResult:
        """
        验证一条路径是否满足 δS=0 (即是否为物理上可行的路径)。

        方法: 对路径做微小扰动, 检查 S 是否变化。
        """
        S0 = self.compute_action(q_path, dt)

        # 扰动: 中间点 ±ε
        max_grad = 0.0
        eps = 0.001 * np.std(q_path) if np.std(q_path) > 1e-10 else 0.001

        for i in range(1, len(q_path) - 1):
            q_plus = q_path.copy()
            q_plus[i] += eps
            S_plus = self.compute_action(q_plus, dt)

            q_minus = q_path.copy()
            q_minus[i] -= eps
            S_minus = self.compute_action(q_minus, dt)

            grad = (S_plus - S_minus) / (2 * eps)
            max_grad = max(max_grad, abs(grad))

        is_stationary = max_grad < self.tolerance * abs(S0) if abs(S0) > 1e-10 else max_grad < self.tolerance

        # Euler-Lagrange 残差
        el_residual = self._euler_lagrange_residual(q_path, dt)

        return ActionResult(
            action=S0,
            is_stationary=is_stationary,
            max_gradient=max_grad,
            euler_lagrange_residual=el_residual,
            path=q_path.copy(),
            notes=f"S={S0:.6f}, max|δS/δq|={max_grad:.6f}"
                  f"{', STATIONARY' if is_stationary else ', NOT stationary'}",
        )

    def find_stationary_path(self, q_start: float, q_end: float,
                             n_steps: int = 100, dt: float = 0.01,
                             n_iterations: int = 500,
                             learning_rate: float = 0.01) -> ActionResult:
        """
        变分优化: 从直线路径开始, 梯度下降寻找 δS=0 的路径。

        这是物理因果路径发现的核心:
          给定初态 q_start 和终态 q_end, 
          找到满足最小作用量原理的真实路径。

        相当于在「所有可能世界线」中选出物理上可行的那一条。
        """
        # 初始化: 线性插值
        path = np.linspace(q_start, q_end, n_steps)

        best_path = path.copy()
        best_S = self.compute_action(path, dt)

        for iteration in range(n_iterations):
            # 计算每个内部点的梯度
            grad = np.zeros(n_steps)
            eps = 1e-4

            for i in range(1, n_steps - 1):
                path[i] += eps
                S_plus = self.compute_action(path, dt)
                path[i] -= 2 * eps
                S_minus = self.compute_action(path, dt)
                path[i] += eps  # 恢复
                grad[i] = (S_plus - S_minus) / (2 * eps)

            # 边界条件: 固定两端
            grad[0] = 0
            grad[-1] = 0

            # 梯度下降
            path = path - learning_rate * grad

            S = self.compute_action(path, dt)
            if S < best_S:
                best_S = S
                best_path = path.copy()

            # 收敛检查
            if np.max(np.abs(grad)) < self.tolerance:
                break

        return self.validate_path(best_path, dt)

    def _euler_lagrange_residual(self, q_path: np.ndarray,
                                  dt: float) -> float:
        """
        计算 Euler-Lagrange 方程的残差。

        d/dt (∂L/∂q̇) - ∂L/∂q = 0

        用数值微分近似。
        """
        eps = 1e-6
        n = len(q_path)
        residuals = []

        for i in range(1, n - 1):
            q = q_path[i]
            q_dot = (q_path[i + 1] - q_path[i - 1]) / (2 * dt)

            # ∂L/∂q̇ 在 q_dot 处
            L_plus = self.L(q, q_dot + eps)
            L_minus = self.L(q, q_dot - eps)
            dL_dqdot = (L_plus - L_minus) / (2 * eps)

            # d/dt (∂L/∂q̇) 用 q_dot 的前后差分
            if i < n - 2:
                q_dot_next = (q_path[i + 2] - q_path[i]) / (2 * dt)
                dL_dqdot_next = (self.L(q, q_dot_next + eps) -
                                 self.L(q, q_dot_next - eps)) / (2 * eps)
                d_dt = (dL_dqdot_next - dL_dqdot) / dt
            else:
                d_dt = 0.0

            # ∂L/∂q
            L_qplus = self.L(q + eps, q_dot)
            L_qminus = self.L(q - eps, q_dot)
            dL_dq = (L_qplus - L_qminus) / (2 * eps)

            residual = abs(d_dt - dL_dq)
            residuals.append(residual)

        return float(np.mean(residuals)) if residuals else 0.0


# ═══════════════════════════════════════════════════════════════
# Noether Bridge: Lagrangian → Conservation Laws
# ═══════════════════════════════════════════════════════════════

class NoetherBridge:
    """
    连接最小作用量原理和对称性模块。

    Noether 定理:
      如果 Lagrangian 在某个连续变换下不变,
      则存在对应的守恒流 (守恒量)。

    变换             不变性条件            守恒量
    ─────────────────────────────────────────────
    t → t + δt       ∂L/∂t = 0           能量 E = q̇·∂L/∂q̇ - L
    q → q + δq       ∂L/∂q = 0           动量 p = ∂L/∂q̇
    θ → θ + δθ       ∂L/∂θ = 0           角动量 L = q × p
    """

    def __init__(self, lagrangian: Lagrangian):
        self.L = lagrangian

    def energy(self, q: float, q_dot: float) -> float:
        """Noether 能量: E = q̇ · ∂L/∂q̇ - L"""
        eps = 1e-6
        L = self.L(q, q_dot)
        L_plus = self.L(q, q_dot + eps)
        dL_dqdot = (L_plus - L) / eps
        return q_dot * dL_dqdot - L

    def is_energy_conserved(self, path: np.ndarray, dt: float,
                            tol: float = 0.05) -> bool:
        """验证能量是否守恒"""
        energies = []
        for i in range(len(path) - 1):
            q = path[i]
            q_dot = (path[i + 1] - path[i]) / dt if i < len(path) - 1 else 0.0
            energies.append(self.energy(q, q_dot))

        if len(energies) < 2:
            return True

        energies = np.array(energies)
        variation = np.std(energies) / (abs(np.mean(energies)) + 1e-10)
        return variation < tol

    def conserved_quantities(self) -> List[str]:
        """列出 Lagrangian 的守恒量"""
        conserved = []
        if hasattr(self.L, 'potential'):
            # 检查势能是否显含坐标 → 动量守恒
            eps = 1e-6
            q_test = 0.5
            V0 = self.L.potential(q_test)
            V1 = self.L.potential(q_test + eps)
            if abs(V0 - V1) < eps:
                conserved.append("momentum (∂L/∂q = 0)")

        # 检查是否显含时间 → 能量守恒
        if not any('t' in v for v in self.L.variables):
            conserved.append("energy (∂L/∂t = 0)")

        return conserved


# ═══════════════════════════════════════════════════════════════
# Causal Path Validation
# ═══════════════════════════════════════════════════════════════

class CausalPathValidator:
    """
    用最小作用量原理验证因果路径。

    在因果推断中的应用:
      1. 物理可行性:  因果路径必须满足 δS=0
      2. 最优因果路径: 在多个路径中等价时, 选作用量最小的
      3. 反事实验证:   反事实轨迹也必须满足物理约束
    """

    def __init__(self, action_principle: ActionPrinciple):
        self.ap = action_principle

    def is_physically_possible(self, cause_state: float,
                                effect_state: float,
                                dt: float = 0.01,
                                n_steps: int = 100) -> Tuple[bool, str]:
        """
        验证从 cause_state 到 effect_state 的因果路径是否物理上可能。

        方法:
          1. 变分优化找到 δS=0 的路径
          2. 检查该路径的终点是否接近 effect_state
          3. 如果连最优路径都到不了, 则该因果假设不可能
        """
        result = self.ap.find_stationary_path(
            cause_state, effect_state, n_steps=n_steps, dt=dt
        )

        if result.is_stationary:
            return True, f"Physically possible: {result.notes}"
        else:
            return False, f"Physically impossible: {result.notes}"

    def rank_causal_paths(self, start: float, end: float,
                          n_candidates: int = 5) -> List[ActionResult]:
        """
        生成多个候选因果路径, 按作用量排序。

        作用量最小的路径 = 最可能的因果路径。
        """
        candidates = []
        for seed in range(n_candidates):
            np.random.seed(seed)
            # 随机初始猜测
            path = np.linspace(start, end, 100)
            path[1:-1] += np.random.normal(0, 0.1 * abs(end - start), 98)

            result = self.ap.validate_path(path, dt=0.01)
            candidates.append(result)

        candidates.sort(key=lambda r: r.action)
        return candidates
