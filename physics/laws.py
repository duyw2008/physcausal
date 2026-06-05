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
            forbidden_directions=[("force", "x")],
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
            forbidden_directions=[("v1_prime", "m1"), ("v1_prime", "v1")],
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
            forbidden_directions=[("voltage", "current"), ("voltage", "resistance")],
        ))
        self.register(PhysicsLaw(
            name="Coulomb", domain="electromagnetism",
            latex=r"F = k q_1 q_2 / r^2",
            inputs=["q1", "q2", "r"], outputs=["force_electric"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda q1, q2, r: 8.99e9 * q1 * q2 / (r * r) if r != 0 else 0.0,
            causal_direction=[("q1", "force_electric"), ("q2", "force_electric"), ("r", "force_electric")],
        ))
        self.register(PhysicsLaw(
            name="Faraday", domain="electromagnetism",
            latex=r"\mathcal{E} = -\frac{d\Phi_B}{dt}",
            inputs=["magnetic_flux_change"], outputs=["induced_emf"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda magnetic_flux_change: -magnetic_flux_change,
            causal_direction=[("magnetic_flux_change", "induced_emf")],
            forbidden_directions=[("induced_emf", "magnetic_flux_change")],
            # 变化的磁场产生电场 — 因果方向不可逆
        ))
        self.register(PhysicsLaw(
            name="Ampere", domain="electromagnetism",
            latex=r"\oint B \cdot dl = \mu_0 I",
            inputs=["current"], outputs=["magnetic_field"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda current: current,
            causal_direction=[("current", "magnetic_field")],
        ))
        self.register(PhysicsLaw(
            name="Lenz", domain="electromagnetism",
            latex=r"感应电流的方向是阻碍磁通量变化的方向",
            inputs=["magnetic_flux_change"], outputs=["induced_current"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda magnetic_flux_change: -magnetic_flux_change,
            causal_direction=[("magnetic_flux_change", "induced_current")],
            forbidden_directions=[("induced_current", "magnetic_flux_change")],
        ))
        self.register(PhysicsLaw(
            name="Joule Heating", domain="electromagnetism",
            latex=r"P = I^2 R",
            inputs=["current", "resistance"], outputs=["heat_power"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda current, resistance: current * current * resistance,
            causal_direction=[("current", "heat_power"), ("resistance", "heat_power")],
            forbidden_directions=[("heat_power", "current")],
            # 热量不能反向驱动电流 (熵增)
        ))
        # ── 热力学 ──
        self.register(PhysicsLaw(
            name="Kinetic Theory", domain="thermodynamics",
            latex=r"T = \frac{2}{3k_B} \langle \frac{1}{2}mv^2 \rangle",
            inputs=["kinetic_energy"], outputs=["temperature"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda kinetic_energy, k_B=1.38e-23: (2/(3*k_B)) * kinetic_energy if k_B != 0 else 0.0,
            causal_direction=[("kinetic_energy", "temperature")],
            forbidden_directions=[("temperature", "kinetic_energy")],
            # 温度是分子平均动能的统计量 — 结构因果方向: KE→T, 不是 T→KE
        ))
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
        self.register(PhysicsLaw(
            name="Continuity", domain="fluids",
            latex=r"A_1 v_1 = A_2 v_2",
            inputs=["cross_section"], outputs=["velocity"],
            constraint_type=ConstraintType.CONSERVATION,
            formula=lambda cross_section, v: 0.0,
            causal_direction=[("cross_section", "velocity")],
            forbidden_directions=[("velocity", "cross_section")],
            # 截面积减小→流速增大 (不可逆因果)
        ))
        self.register(PhysicsLaw(
            name="Poiseuille", domain="fluids",
            latex=r"Q = \frac{\pi r^4}{8\eta} \frac{\Delta P}{L}",
            inputs=["radius", "pressure_diff", "viscosity", "length"],
            outputs=["flow_rate"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda radius, pressure_diff, viscosity, length: 
                np.pi * radius**4 * pressure_diff / (8 * viscosity * length) if viscosity * length != 0 else 0.0,
            causal_direction=[("radius", "flow_rate"), ("pressure_diff", "flow_rate")],
        ))
        # ── 光学 ──
        self.register(PhysicsLaw(
            name="Locality", domain="relativity",
            latex=r"\Delta s^2 = c^2\Delta t^2  - \Delta x^2 \geq 0",
            inputs=["time", "distance"], outputs=["causal_possible"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda time, distance, c=3e8: 1 if c * time >= distance else 0,
            causal_direction=[],
            forbidden_directions=[],
            # 局域因果: 原因必须在结果的光锥之内
            # 类空间隔的事件不能有直接因果联系
            # 这不是元规律——Newton 力学里因果是瞬时的
            # 只是在我们的宇宙里, SR 是正确的
        ))
        # ── 光学 ──
        self.register(PhysicsLaw(
            name="Snell", domain="optics",
            latex=r"n_1 \sin\theta_1 = n_2 \sin\theta_2",
            inputs=["n1", "n2", "incident_angle"], outputs=["refraction_angle"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda n1, n2, incident_angle: 
                np.arcsin(n1 * np.sin(incident_angle) / n2) if n2 != 0 else 0.0,
            causal_direction=[("n1", "refraction_angle"), ("n2", "refraction_angle"), 
                            ("incident_angle", "refraction_angle")],
            forbidden_directions=[("refraction_angle", "incident_angle")],
        ))
        self.register(PhysicsLaw(
            name="Lens", domain="optics",
            latex=r"\frac{1}{f} = \frac{1}{u} + \frac{1}{v}",
            inputs=["object_distance", "focal_length"], outputs=["image_distance"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda object_distance, focal_length: 
                1 / (1/focal_length - 1/object_distance) if abs(1/focal_length - 1/object_distance) > 1e-10 else 0.0,
            causal_direction=[("object_distance", "image_distance"), ("focal_length", "image_distance")],
        ))
        self.register(PhysicsLaw(
            name="Reflection", domain="optics",
            latex=r"\theta_i = \theta_r",
            inputs=["incident_angle"], outputs=["reflection_angle"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda incident_angle: incident_angle,
            causal_direction=[("incident_angle", "reflection_angle")],
            forbidden_directions=[("reflection_angle", "incident_angle")],
        ))
        # ── 声学 ──
        self.register(PhysicsLaw(
            name="WaveSpeed", domain="acoustics",
            latex=r"v = \lambda f",
            inputs=["wavelength", "frequency"], outputs=["wave_speed"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda wavelength, frequency: wavelength * frequency,
            causal_direction=[("wavelength", "wave_speed"), ("frequency", "wave_speed")],
        ))
        self.register(PhysicsLaw(
            name="Doppler", domain="acoustics",
            latex=r"f' = f \frac{v \pm v_o}{v \mp v_s}",
            inputs=["source_frequency", "source_velocity", "observer_velocity"],
            outputs=["observed_frequency"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda source_frequency, source_velocity, observer_velocity, v_sound=343:
                source_frequency * (v_sound + observer_velocity) / (v_sound - source_velocity) if v_sound != source_velocity else source_frequency,
            causal_direction=[("source_velocity", "observed_frequency"), 
                            ("observer_velocity", "observed_frequency")],
            forbidden_directions=[("observed_frequency", "source_velocity")],
        ))


# 全局单例
library = PhysicsLibrary()
