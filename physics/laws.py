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
            name="Simple Harmonic", domain="mechanics",
            latex=r"\omega = \sqrt{k/m}",
            inputs=["elastic_constant", "m"], outputs=["angular_velocity"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda elastic_constant, m: np.sqrt(elastic_constant / m) if m > 0 else 0.0,
            causal_direction=[("elastic_constant", "angular_velocity"), ("m", "angular_velocity")],
            forbidden_directions=[("angular_velocity", "elastic_constant"), ("angular_velocity", "m")],
        ))
        self.register(PhysicsLaw(
            name="Momentum Conservation", domain="mechanics",
            latex=r"m_1 v_1 + m_2 v_2 = m_1 v_1' + m_2 v_2'",
            inputs=["m1", "m2", "v1", "v2"], outputs=["v1_prime", "v2_prime"],
            constraint_type=ConstraintType.CONSERVATION,
            causal_direction=[
                ("m1", "v1_prime"), ("v1", "v1_prime"),
                ("m2", "v1_prime"), ("v2", "v1_prime"),
                ("m1", "v2_prime"), ("v1", "v2_prime"),
                ("m2", "v2_prime"), ("v2", "v2_prime"),
            ],
            forbidden_directions=[
                ("v1_prime", "m1"), ("v1_prime", "v1"),
                ("v2_prime", "m2"), ("v2_prime", "v2"),
            ],
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
            latex=r"\mathcal{E} = -N \frac{d\Phi_B}{dt}",
            inputs=["magnetic_flux_change", "coil_turns"], outputs=["induced_emf"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda magnetic_flux_change, coil_turns=1: -coil_turns * magnetic_flux_change,
            causal_direction=[("magnetic_flux_change", "induced_emf"), ("coil_turns", "induced_emf")],
            forbidden_directions=[("induced_emf", "magnetic_flux_change"), ("induced_emf", "coil_turns")],
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
            name="Entropy Increase", domain="thermodynamics",
            latex=r"\Delta S \geq 0",
            inputs=["system_state"], outputs=["entropy"],
            constraint_type=ConstraintType.CONSERVATION,
            formula=lambda system_state: 0.0,
            causal_direction=[("system_state", "entropy")],
            forbidden_directions=[("entropy", "system_state")],
            # 第二定律: 孤立系统的熵不减 → 时间箭头
        ))
        self.register(PhysicsLaw(
            name="Ideal Gas", domain="thermodynamics",
            latex=r"PV = nRT",
            inputs=["n", "temperature"], outputs=["pressure", "volume"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda n, temperature, volume=1.0: n * 8.314 * temperature / volume if volume != 0 else 0.0,
            causal_direction=[("temperature", "pressure"), ("temperature", "volume"),
                            ("n", "pressure"), ("n", "volume")],
            forbidden_directions=[("pressure", "temperature"), ("volume", "temperature")],
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
            causal_direction=[("source_frequency", "observed_frequency"),
                            ("source_velocity", "observed_frequency"), 
                            ("observer_velocity", "observed_frequency")],
            forbidden_directions=[("observed_frequency", "source_velocity"),
                                ("observed_frequency", "source_frequency")],
        ))
        # ── 热力学扩展 ──
        self.register(PhysicsLaw(
            name="StefanBoltzmann", domain="thermodynamics",
            latex=r"P = \sigma A T^4",
            inputs=["temperature", "area"], outputs=["radiated_power"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda temperature, area, sigma=5.67e-8: sigma * area * temperature**4,
            causal_direction=[("temperature", "radiated_power"), ("area", "radiated_power")],
            forbidden_directions=[("radiated_power", "temperature")],
        ))
        self.register(PhysicsLaw(
            name="NewtonCooling", domain="thermodynamics",
            latex=r"\frac{dT}{dt} = -k(T - T_{env})",
            inputs=["temperature_diff"], outputs=["cooling_rate"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda temperature_diff, k=0.1: k * temperature_diff,
            causal_direction=[("temperature_diff", "cooling_rate")],
            forbidden_directions=[("cooling_rate", "temperature_diff")],
        ))
        # ── 流体力学 ──
        self.register(PhysicsLaw(
            name="Archimedes", domain="fluids",
            latex=r"F_b = \rho g V",
            inputs=["fluid_density", "volume"], outputs=["buoyant_force"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda fluid_density, volume, g=9.8: fluid_density * g * volume,
            causal_direction=[("fluid_density", "buoyant_force"), ("volume", "buoyant_force")],
            forbidden_directions=[("buoyant_force", "fluid_density"), ("buoyant_force", "volume")],
        ))
        # ── 电磁学扩展 ──
        self.register(PhysicsLaw(
            name="Lorentz", domain="electromagnetism",
            latex=r"F = q(E + v \times B)",
            inputs=["charge", "velocity", "magnetic_field"], outputs=["lorentz_force"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda charge, velocity, magnetic_field: charge * velocity * magnetic_field,
            causal_direction=[("charge", "lorentz_force"), ("velocity", "lorentz_force"),
                            ("magnetic_field", "lorentz_force")],
            forbidden_directions=[("lorentz_force", "charge"), ("lorentz_force", "magnetic_field")],
        ))
        # ── 现代物理 ──
        self.register(PhysicsLaw(
            name="MassEnergy", domain="modern",
            latex=r"E = mc^2",
            inputs=["mass"], outputs=["energy"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda mass, c=3e8: mass * c**2,
            causal_direction=[("mass", "energy")],
            forbidden_directions=[("energy", "mass")],
        ))
        self.register(PhysicsLaw(
            name="Photoelectric", domain="modern",
            latex=r"E = hf - \phi",
            inputs=["frequency"], outputs=["electron_energy"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda frequency, h=6.63e-34, phi=2.0: h * frequency - phi,
            causal_direction=[("frequency", "electron_energy")],
            forbidden_directions=[("electron_energy", "frequency")],
        ))
        # ── 量子力学 ──
        self.register(PhysicsLaw(
            name="deBroglie", domain="quantum",
            latex=r"\lambda = h / p",
            inputs=["momentum"], outputs=["wavelength"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda momentum, h=6.63e-34: h / momentum if momentum != 0 else float('inf'),
            causal_direction=[("momentum", "wavelength")],
            forbidden_directions=[("wavelength", "momentum")],
            # 波粒二象性: 动量越大, 波长越短
        ))
        self.register(PhysicsLaw(
            name="HeisenbergUncertainty", domain="quantum",
            latex=r"\Delta x \Delta p \geq \hbar/2",
            inputs=["position_uncertainty", "momentum_uncertainty"],
            outputs=[], constraint_type=ConstraintType.CONSERVATION,
            formula=lambda position_uncertainty, momentum_uncertainty: position_uncertainty * momentum_uncertainty,
            causal_direction=[],
            forbidden_directions=[],
            # 不确定原理: 位置和动量不能同时精确确定
        ))
        self.register(PhysicsLaw(
            name="BornRule", domain="quantum",
            latex=r"P = |\psi|^2",
            inputs=["wave_function"], outputs=["probability"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda wave_function: abs(wave_function)**2,
            causal_direction=[("wave_function", "probability")],
            forbidden_directions=[("probability", "wave_function")],
            # 概率幅 → 观测概率 (测量坍缩)
        ))
        self.register(PhysicsLaw(
            name="NoCommunication", domain="quantum",
            latex=r"\text{entanglement} \nRightarrow \text{signaling}",
            inputs=["measurement_outcome"], outputs=[],
            constraint_type=ConstraintType.CONSERVATION,
            formula=lambda measurement_outcome: 0.0,
            causal_direction=[],
            forbidden_directions=[],
            # 量子纠缠不能用于超光速通信
        ))
        self.register(PhysicsLaw(
            name="PauliExclusion", domain="quantum",
            latex=r"\text{no two fermions share all quantum numbers}",
            inputs=["quantum_state"], outputs=["occupation_limit"],
            constraint_type=ConstraintType.CONSERVATION,
            formula=lambda quantum_state: 1.0,
            causal_direction=[("quantum_state", "occupation_limit")],
            forbidden_directions=[],
            # 泡利不相容: 每个量子态最多一个费米子
        ))
        self.register(PhysicsLaw(
            name="EnergyQuantization", domain="quantum",
            latex=r"E_n = (n + 1/2)\hbar\omega",
            inputs=["quantum_number"], outputs=["energy_level"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda quantum_number, hbar=1.05e-34, omega=1: (quantum_number + 0.5) * hbar * omega,
            causal_direction=[("quantum_number", "energy_level")],
            forbidden_directions=[("energy_level", "quantum_number")],
            # 能量量子化: 离散能级
        ))
        # ── 广义相对论 ──
        self.register(PhysicsLaw(
            name="Schwarzschild", domain="general_relativity",
            latex=r"r_s = 2GM/c^2",
            inputs=["mass"], outputs=["schwarzschild_radius"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda mass, G=6.67e-11, c=3e8: 2 * G * mass / c**2,
            causal_direction=[("mass", "schwarzschild_radius")],
            forbidden_directions=[("schwarzschild_radius", "mass")],
            # 史瓦西半径: 质量越大, 事件视界越大
        ))
        self.register(PhysicsLaw(
            name="TimeDilation", domain="general_relativity",
            latex=r"t' = t \sqrt{1 - v^2/c^2}",
            inputs=["velocity"], outputs=["dilated_time"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda velocity, rest_time=1.0, c=3e8: rest_time / np.sqrt(1 - velocity**2 / c**2) if velocity < c else float('inf'),
            causal_direction=[("velocity", "dilated_time")],
            forbidden_directions=[("dilated_time", "velocity")],
            # 时间膨胀: 速度越快, 时间越慢
        ))
        self.register(PhysicsLaw(
            name="GravitationalRedshift", domain="general_relativity",
            latex=r"\Delta f / f = g\Delta h / c^2",
            inputs=["gravity", "height"], outputs=["frequency_shift"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda gravity, height, c=3e8: gravity * height / c**2,
            causal_direction=[("gravity", "frequency_shift"), ("height", "frequency_shift")],
            forbidden_directions=[("frequency_shift", "gravity")],
            # 引力红移: 光爬出引力场时频率降低
        ))
        self.register(PhysicsLaw(
            name="EquivalencePrinciple", domain="general_relativity",
            latex=r"\text{gravity} \equiv \text{acceleration}",
            inputs=["gravitational_mass", "inertial_mass"], outputs=[],
            constraint_type=ConstraintType.CONSERVATION,
            formula=lambda gravitational_mass, inertial_mass: gravitational_mass / inertial_mass if inertial_mass != 0 else 0,
            causal_direction=[],
            forbidden_directions=[],
            # 等效原理: 引力质量 = 惯性质量, 引力不可区分于加速
        ))


# 全局单例
library = PhysicsLibrary()
