"""
物理仿真环境 — 可交互的因果实验平台

提供可配置的物理系统，智能体可以通过干预来发现因果结构。

环境接口:
  - step(intervention) → observation
  - reset() → 新场景
  - get_ground_truth() → 真实因果图 (用于评估)

场景:
  - Pendulum:   L, g → T (周期)
  - Collision:  m1,v1,m2,v2 → v1',v2'
  - Spring:     k, m → ω (频率)
  - Circuit:    V, R → I
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class PhysicsEnv:
    """物理仿真环境基类"""
    name: str
    variables: List[str]
    ground_truth_edges: List[Tuple[str, str]]
    domain: str = "mechanics"
    noise_std: float = 0.1

    def observe(self) -> Dict[str, float]:
        """获取当前观测"""
        raise NotImplementedError

    def intervene(self, var: str, value: float) -> Dict[str, float]:
        """
        干预: do(var = value)
        
        Returns:
            干预后的观测值 (所有变量)
        """
        raise NotImplementedError

    def step(self, n: int = 1) -> np.ndarray:
        """运行 n 步并收集数据 → (n, n_vars)"""
        rows = []
        for _ in range(n):
            obs = self.observe()
            rows.append([obs[v] for v in self.variables])
        return np.array(rows)

    def experiment(self, intervention: Dict[str, float],
                   n_samples: int = 100) -> np.ndarray:
        """执行干预实验，收集数据"""
        # 保存原状态，执行干预，恢复
        original = self.observe()
        for var, val in intervention.items():
            self.intervene(var, val)
        data = self.step(n_samples)
        # 无法简单恢复，reset
        self.reset()
        return data

    def reset(self):
        """重置环境"""
        pass

    def variable_info(self) -> Dict:
        return {
            "name": self.name,
            "domain": self.domain,
            "variables": self.variables,
            "ground_truth": self.ground_truth_edges,
        }


# ═══════════════════════════════════════════════════════════════
# Pendulum
# ═══════════════════════════════════════════════════════════════

class PendulumEnv(PhysicsEnv):
    """单摆: T = 2π√(L/g)"""
    
    def __init__(self, noise_std: float = 0.02):
        super().__init__(
            name="pendulum",
            variables=["L", "g", "T"],
            ground_truth_edges=[("L", "T"), ("g", "T")],
            domain="mechanics",
            noise_std=noise_std,
        )
        self.L = 1.0
        self.g = 9.81
        self.reset()

    def reset(self):
        rng = np.random
        self.L = rng.uniform(0.5, 2.0)
        self.g = rng.uniform(1.0, 20.0)

    def observe(self) -> Dict[str, float]:
        T = 2 * np.pi * np.sqrt(self.L / self.g)
        T += np.random.normal(0, self.noise_std * T)
        return {"L": self.L, "g": self.g, "T": T}

    def intervene(self, var: str, value: float) -> Dict[str, float]:
        if var == "L":
            self.L = value
        elif var == "g":
            self.g = value
        # 不能干预 T — 它是果
        return self.observe()


# ═══════════════════════════════════════════════════════════════
# Collision
# ═══════════════════════════════════════════════════════════════

class CollisionEnv(PhysicsEnv):
    """弹性碰撞: m1,v1,m2,v2 → v1',v2'"""
    
    def __init__(self, noise_std: float = 0.05):
        super().__init__(
            name="collision",
            variables=["m1", "v1", "m2", "v2", "v1p", "v2p"],
            ground_truth_edges=[
                ("m1", "v1p"), ("v1", "v1p"),
                ("m2", "v1p"), ("v2", "v1p"),
                ("m1", "v2p"), ("v1", "v2p"),
                ("m2", "v2p"), ("v2", "v2p"),
            ],
            domain="mechanics",
            noise_std=noise_std,
        )
        self.m1 = 1.0; self.m2 = 1.0
        self.v1 = 2.0; self.v2 = 0.0
        self.reset()

    def reset(self):
        rng = np.random
        self.m1 = rng.uniform(0.5, 2.0)
        self.m2 = rng.uniform(0.5, 2.0)
        self.v1 = rng.uniform(1.0, 5.0)
        self.v2 = rng.uniform(-3.0, 1.0)

    def observe(self) -> Dict[str, float]:
        denom = self.m1 + self.m2
        v1p = (self.m1 - self.m2) * self.v1 / denom + 2 * self.m2 * self.v2 / denom
        v2p = 2 * self.m1 * self.v1 / denom + (self.m2 - self.m1) * self.v2 / denom
        v1p += np.random.normal(0, self.noise_std)
        v2p += np.random.normal(0, self.noise_std)
        return {"m1": self.m1, "v1": self.v1, "m2": self.m2,
                "v2": self.v2, "v1p": v1p, "v2p": v2p}

    def intervene(self, var: str, value: float) -> Dict[str, float]:
        if var == "m1": self.m1 = value
        elif var == "v1": self.v1 = value
        elif var == "m2": self.m2 = value
        elif var == "v2": self.v2 = value
        return self.observe()


# ═══════════════════════════════════════════════════════════════
# Circuit
# ═══════════════════════════════════════════════════════════════

class CircuitEnv(PhysicsEnv):
    """电路: V, R → I (Ohm 定律)"""
    
    def __init__(self, noise_std: float = 0.03):
        super().__init__(
            name="circuit",
            variables=["V", "R", "I"],
            ground_truth_edges=[("V", "I"), ("R", "I")],
            domain="electromagnetism",
            noise_std=noise_std,
        )
        self.V = 5.0
        self.R = 10.0
        self.reset()

    def reset(self):
        rng = np.random
        self.V = rng.uniform(1, 12)
        self.R = rng.uniform(1, 100)

    def observe(self) -> Dict[str, float]:
        I = self.V / self.R + np.random.normal(0, self.noise_std * self.V / self.R)
        return {"V": self.V, "R": self.R, "I": I}

    def intervene(self, var: str, value: float) -> Dict[str, float]:
        if var == "V": self.V = value
        elif var == "R": self.R = value
        return self.observe()


# ═══════════════════════════════════════════════════════════════
# Spring
# ═══════════════════════════════════════════════════════════════

class SpringEnv(PhysicsEnv):
    """弹簧振子: k, m → ω (频率 ω = √(k/m))"""
    
    def __init__(self, noise_std: float = 0.05):
        super().__init__(
            name="spring",
            variables=["k", "m", "omega"],
            ground_truth_edges=[("k", "omega"), ("m", "omega")],
            domain="mechanics",
            noise_std=noise_std,
        )
        self.k = 10.0
        self.m = 1.0
        self.reset()

    def reset(self):
        rng = np.random
        self.k = rng.uniform(1, 50)
        self.m = rng.uniform(0.1, 5.0)

    def observe(self) -> Dict[str, float]:
        omega = np.sqrt(self.k / self.m)
        omega += np.random.normal(0, self.noise_std * omega)
        return {"k": self.k, "m": self.m, "omega": omega}

    def intervene(self, var: str, value: float) -> Dict[str, float]:
        if var == "k": self.k = value
        elif var == "m": self.m = value
        return self.observe()


# ═══════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════

ENV_REGISTRY = {
    "pendulum": PendulumEnv,
    "collision": CollisionEnv,
    "circuit": CircuitEnv,
    "spring": SpringEnv,
}

def make_env(name: str) -> PhysicsEnv:
    return ENV_REGISTRY[name]()
