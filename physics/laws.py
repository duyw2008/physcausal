"""
物理层 — 物理定律作为因果结构的硬约束

从 causal_agent 的 core/physics.py 迁移并增强。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np


# ═══════════════════════════════════════════════════════════════
# Constraint Types
# ═══════════════════════════════════════════════════════════════

class ConstraintType(Enum):
    SCM_EQUATION = auto()    # 替换 SCM 方程
    CONSERVATION = auto()    # 验证守恒律
    DAG_EDGE = auto()        # 强制/禁止因果边
    BOUNDARY = auto()        # 边界条件
    SYMMETRY = auto()        # 对称性约束


# ═══════════════════════════════════════════════════════════════
# PhysicsLaw
# ═══════════════════════════════════════════════════════════════

@dataclass
class PhysicsLaw:
    """单条物理定律"""
    name: str
    domain: str                     # mechanics, electromagnetism, ...
    latex: str                      # LaTeX 公式
    inputs: List[str]               # 输入变量名
    outputs: List[str]              # 输出变量名
    constraint_type: ConstraintType
    formula: Callable[..., float]   # Python 可调用函数
    causal_direction: List[Tuple[str, str]] = field(default_factory=list)
    # 例: [("Force", "Acceleration"), ("Length", "Period")]
    forbidden_directions: List[Tuple[str, str]] = field(default_factory=list)
    # 例: [("Velocity", "Mass")]  — 因果方向错误
    required_parents: Dict[str, List[str]] = field(default_factory=dict)
    # 例: {"Acceleration": ["Force", "Mass"]}
    tolerance: float = 0.02

    def validate(self, values: Dict[str, float]) -> bool:
        """验证数据是否满足此定律"""
        try:
            args = {v: values.get(v, 0.0) for v in self.inputs}
            predicted = self.formula(**args)
            for out in self.outputs:
                if out in values:
                    if abs(values[out] - predicted) > self.tolerance:
                        return False
            return True
        except Exception:
            return False


# ═══════════════════════════════════════════════════════════════
# PhysicsLibrary — 定律注册表
# ═══════════════════════════════════════════════════════════════

class PhysicsLibrary:
    """物理定律库。可动态注册/查询定律。"""

    def __init__(self):
        self._laws: List[PhysicsLaw] = []
        self._register_default_laws()

    def register(self, law: PhysicsLaw):
        self._laws.append(law)

    def list_by_domain(self, domain: str) -> List[PhysicsLaw]:
        return [l for l in self._laws if l.domain == domain]

    def list_all(self) -> List[PhysicsLaw]:
        return list(self._laws)

    def find_relevant(self, variable_names: List[str]) -> List[PhysicsLaw]:
        """通过变量名交集查找相关定律"""
        matched = []
        vset = set(variable_names)
        for law in self._laws:
            law_vars = set(law.inputs + law.outputs)
            if law_vars & vset:
                matched.append(law)
        return matched

    def forced_edges(self, variable_names: List[str]) -> List[Tuple[str, str]]:
        """返回物理定律强制要求的因果边"""
        edges = []
        for law in self.find_relevant(variable_names):
            edges.extend(law.causal_direction)
        return edges

    def forbidden_edges(self, variable_names: List[str]) -> List[Tuple[str, str]]:
        """返回物理定律禁止的因果边"""
        edges = []
        for law in self.find_relevant(variable_names):
            edges.extend(law.forbidden_directions)
        return edges

    def _register_default_laws(self):
        # ── 力学 ──
        self.register(PhysicsLaw(
            name="Newton II", domain="mechanics",
            latex=r"F = m a",
            inputs=["mass", "force"], outputs=["acceleration"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda mass, force: force / mass if mass != 0 else 0.0,
            causal_direction=[("force", "acceleration")],
            forbidden_directions=[("acceleration", "mass")],
            required_parents={"acceleration": ["force", "mass"]},
        ))
        self.register(PhysicsLaw(
            name="Hooke", domain="mechanics",
            latex=r"F = -k x",
            inputs=["k", "x"], outputs=["force"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda k, x: -k * x,
            causal_direction=[("x", "force")],
        ))
        self.register(PhysicsLaw(
            name="Gravity", domain="mechanics",
            latex=r"F = G m_1 m_2 / r^2",
            inputs=["m1", "m2", "r"], outputs=["force_gravity"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda m1, m2, r: 6.674e-11 * m1 * m2 / (r * r) if r != 0 else 0.0,
            causal_direction=[("m1", "force_gravity"), ("m2", "force_gravity"), ("r", "force_gravity")],
        ))
        self.register(PhysicsLaw(
            name="Pendulum Period", domain="mechanics",
            latex=r"T = 2\pi\sqrt{L/g}",
            inputs=["length", "g"], outputs=["period"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda length, g: 2 * np.pi * np.sqrt(length / g) if g != 0 else 0.0,
            causal_direction=[("length", "period"), ("g", "period")],
            forbidden_directions=[("period", "length")],
        ))
        self.register(PhysicsLaw(
            name="Momentum Conservation", domain="mechanics",
            latex=r"m_1 v_1 + m_2 v_2 = m_1 v_1' + m_2 v_2'",
            inputs=["m1", "m2", "v1", "v2"], outputs=["v1_prime", "v2_prime"],
            constraint_type=ConstraintType.CONSERVATION,
            formula=lambda m1, m2, v1, v2: 0.0,  # 守恒律 — 用于验证而非替换
        ))
        self.register(PhysicsLaw(
            name="Kinetic Energy", domain="mechanics",
            latex=r"E_k = \frac{1}{2} m v^2",
            inputs=["mass", "velocity"], outputs=["kinetic_energy"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda mass, velocity: 0.5 * mass * velocity * velocity,
            causal_direction=[("mass", "kinetic_energy"), ("velocity", "kinetic_energy")],
        ))
        # ── 电磁学 ──
        self.register(PhysicsLaw(
            name="Ohm", domain="electromagnetism",
            latex=r"V = I R",
            inputs=["current", "resistance"], outputs=["voltage"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda current, resistance: current * resistance,
            causal_direction=[("current", "voltage"), ("resistance", "voltage")],
        ))
        self.register(PhysicsLaw(
            name="Coulomb", domain="electromagnetism",
            latex=r"F = k q_1 q_2 / r^2",
            inputs=["q1", "q2", "r"], outputs=["force_electric"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda q1, q2, r: 8.99e9 * q1 * q2 / (r * r) if r != 0 else 0.0,
            causal_direction=[("q1", "force_electric"), ("q2", "force_electric"), ("r", "force_electric")],
        ))
        # ── 热力学 ──
        self.register(PhysicsLaw(
            name="Ideal Gas", domain="thermodynamics",
            latex=r"PV = nRT",
            inputs=["n", "temperature"], outputs=["pressure"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda n, temperature, volume=1.0: n * 8.314 * temperature / volume if volume != 0 else 0.0,
            # Note: volume as kwarg for flexibility
        ))
        # ── 流体 ──
        self.register(PhysicsLaw(
            name="Bernoulli", domain="fluids",
            latex=r"P + \frac{1}{2}\rho v^2 + \rho gh = const",
            inputs=["density", "velocity", "height"], outputs=["pressure"],
            constraint_type=ConstraintType.CONSERVATION,
            formula=lambda density, velocity, height: 0.0,  # 用于验证
        ))


# 全局单例
library = PhysicsLibrary()
