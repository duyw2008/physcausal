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
    collapse_timescale: Optional[str] = None
    # 坍缩时间尺度 (仅量子测量相关定律):
    #   "instantaneous (postulate)" — 哥本哈根坍缩 (公设, 不计时)
    #   "finite (~1/γ)" — 退相干特征时间
    #   "stochastic (rate λ)" — GRW/CSL 客观坍缩
    #   None — 不涉及坍缩时间
    tolerance: float = 0.02
    confidence_tier: int = 1
    # 置信层级 — 防止未经验证的假说污染因果推理:
    #   0 — 公理 (E=mc², F=ma, 热力学定律)
    #   1 — 共识 (de Broglie, Schwarzschild, 标准模型) [默认]
    #   2 — 主流理论 (退相干, 暴胀, 希格斯机制)
    #   3 — 严肃假说 (Penrose 坍缩, de Broglie-Bohm, 多世界)
    #   4 — 探索性编码 (SpacetimeWavelength, 自发现定律)

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
            name="LandauerPrinciple", domain="thermodynamics",
            latex=r"E_{\text{erase}} \geq kT \ln 2",
            inputs=["information_erased"], outputs=["entropy"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda information_erased, k=1.38e-23, T=300: information_erased * k * T * 0.693,
            causal_direction=[("information_erased", "entropy")],
            forbidden_directions=[("entropy", "information_erased")],
            # Landauer 原理 (1961): 擦除 1 比特 → 至少产生 kT ln 2 热量
            # 信息是物理的 — 不是比喻, 是必须付出热力学代价
            # Maxwell 妖的死刑: 妖的记忆满了必须擦除 → 擦除产生熵 → 妖失败
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
        # ── 相变: 热力学→结构桥 ──
        self.register(PhysicsLaw(
            name="PhaseTransition", domain="thermodynamics",
            latex=r"F = U - TS \rightarrow \text{minimize at equilibrium}",
            inputs=["temperature", "entropy"], outputs=["order_parameter"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda temperature, entropy: 1.0 if temperature / (entropy + 1) < 1 else 0.0,
            causal_direction=[("temperature", "order_parameter"), ("entropy", "order_parameter")],
            forbidden_directions=[("order_parameter", "temperature")],
            # 相变: 温度+熵 → 序参量突变 → 对称破缺 → 新结构涌现
            # 这是"稳定→结构"的最直接因果表达
        ))
        self.register(PhysicsLaw(
            name="SymmetryBreaking", domain="thermodynamics",
            latex=r"\langle\phi\rangle = 0 \rightarrow \langle\phi\rangle \neq 0",
            inputs=["order_parameter"], outputs=["phase"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda order_parameter: order_parameter,
            causal_direction=[("order_parameter", "phase")],
            forbidden_directions=[("phase", "order_parameter")],
            # 对称破缺: 序参量非零 → 高对称相→低对称相
            # 已有独立模块 physics/symmetry_breaking.py (SymmetryBreakingDetector)
            # 本定律为其因果图接口
        ))
        # ── 流体 ──
        self.register(PhysicsLaw(
            name="Angular Momentum", domain="mechanics",
            latex=r"L = I\omega = \text{const}",
            inputs=["moment_of_inertia", "angular_velocity"], outputs=[],
            constraint_type=ConstraintType.CONSERVATION,
            formula=lambda moment_of_inertia, angular_velocity: moment_of_inertia * angular_velocity,
            causal_direction=[("moment_of_inertia", "angular_velocity")],
            forbidden_directions=[("angular_velocity", "moment_of_inertia")],
            # 角动量守恒: 无外力矩时 L 不变, 旋转不会停止
        ))
        self.register(PhysicsLaw(
            name="Kepler III", domain="mechanics",
            latex=r"T^2 \propto a^3",
            inputs=["orbital_radius"], outputs=["orbital_period"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda orbital_radius: orbital_radius ** 1.5,
            causal_direction=[("orbital_radius", "orbital_period")],
            forbidden_directions=[("orbital_period", "orbital_radius")],
            # 开普勒第三定律: 轨道半径越大, 周期越长
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
        self.register(PhysicsLaw(
            name="MediumRefraction", domain="optics",
            latex=r"n = \sqrt{1 + \frac{N e^2}{\varepsilon_0 m (\omega_0^2 - \omega^2)}}",
            inputs=["electron_density", "light_frequency"], outputs=["refractive_index"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda electron_density, light_frequency, omega_0=1.0:
                1.0 + 0.01 * electron_density,
            causal_direction=[("electron_density", "refractive_index"),
                            ("light_frequency", "refractive_index")],
            forbidden_directions=[("refractive_index", "electron_density")],
            # 介质折射: 入射光的电场驱动电子振荡 → 电子再辐射 → 相位延迟
            # 折射率 n 取决于电子密度 N 和光频率 ω 与共振频率 ω₀ 的关系
            # n > 1 → v = c/n < c → 光在介质中"表观减速"
            # 出水后: 没有电子 → 没有相位延迟 → 回到 c
            # 能量从未丢失 — 只是叠加波的相位被推迟了 (Feynman)
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
        # Jacobi-Maupertuis 几何化: 恒能系统的轨迹是配置空间中的测地线
        self.register(PhysicsLaw(
            name="JacobiMetric", domain="mechanics",
            latex=r"ds^2 = 2(E - V(q)) T dt^2",
            inputs=["energy", "potential_energy", "kinetic_energy"],
            outputs=["geodesic_path"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda energy, potential_energy, kinetic_energy: 2 * (energy - potential_energy) * kinetic_energy,
            causal_direction=[
                ("energy", "geodesic_path"),
                ("potential_energy", "geodesic_path"),
                ("kinetic_energy", "geodesic_path"),
            ],
            forbidden_directions=[
                ("geodesic_path", "potential_energy"),
            ],
            # Jacobi 度规: 经典力学可以完全几何化 — 即使有势能 V
            # 物理轨迹 = 配置空间中以 ds²=2(E-V)T dt² 为度规的测地线
            # 势能不阻止几何化，它改变了几何 (弯曲了能量面)
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
            name="WaveInterference", domain="quantum",
            latex=r"\Delta x = n\lambda \rightarrow \text{constructive}",
            inputs=["wavelength", "path_difference"], outputs=["interference_pattern"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda wavelength, path_difference:
                1.0 if abs(path_difference % wavelength) < wavelength * 0.1 else 0.0,
            causal_direction=[("wavelength", "interference_pattern"),
                            ("path_difference", "interference_pattern")],
            forbidden_directions=[("interference_pattern", "wavelength")],
            # 波干涉: λ 和路径差 Δx 决定干涉图案
            # Δx = nλ → 建设性 (亮纹), Δx = (n+½)λ → 破坏性 (暗纹)
            # 双缝实验中, 缝距 d 和屏距 L 决定 path_difference = d·sin(θ) ≈ d·y/L
            # 至此几何化完成: mass → curvature → geodesic → wavelength → interference
        ))
        self.register(PhysicsLaw(
            name="PathIntegral", domain="quantum",
            latex=r"\langle x_f | x_i \rangle = \int \mathcal{D}x \, e^{iS[x]/\hbar}",
            inputs=["action"], outputs=["quantum_amplitude"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda action, hbar=1.0: 1.0 if abs(action % (2*3.14159*hbar)) < 0.1 else 0.5,
            causal_direction=[("action", "quantum_amplitude")],
            forbidden_directions=[("quantum_amplitude", "action")],
            # 路径积分: 经典作用量 S → 量子振幅 e^{iS/ħ}
            # 这是几何与量子之间的桥梁 — 最小作用量 δS=0 是 ħ→0 的经典极限
        ))
        # ── δS=0 的推导链路 ──
        self.register(PhysicsLaw(
            name="EulerLagrange", domain="mechanics",
            latex=r"\frac{d}{dt}\frac{\partial L}{\partial \dot{q}} - \frac{\partial L}{\partial q} = 0",
            inputs=["action"], outputs=["force"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda action: action * 0.1,
            causal_direction=[("action", "force")],
            forbidden_directions=[("force", "action")],
            # Euler-Lagrange 方程: 最小作用量 → 运动方程 → 力
            # δS=0 直接产生 Newton 力学 (F=ma)
        ))
        self.register(PhysicsLaw(
            name="HilbertAction", domain="general_relativity",
            latex=r"S_{\text{EH}} = \frac{1}{16\pi G}\int R\sqrt{-g}\,d^4x",
            inputs=["action"], outputs=["spacetime_curvature"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda action, G=6.67e-11: action * G,
            causal_direction=[("action", "spacetime_curvature")],
            forbidden_directions=[("spacetime_curvature", "action")],
            # Einstein-Hilbert 作用量: δS=0 → 爱因斯坦场方程 → 时空曲率
            # action 是真正的根 — 从它出发可以推导 Newton 和 GR
        ))
        # ── 自旋: 量子→磁性桥 ──
        self.register(PhysicsLaw(
            name="SpinMagneticMoment", domain="quantum",
            latex=r"\mu = -g \frac{e}{2m} S",
            inputs=["spin_angular_momentum"], outputs=["magnetic_moment"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda spin: spin * 1.76e11,
            causal_direction=[("spin_angular_momentum", "magnetic_moment")],
            forbidden_directions=[("magnetic_moment", "spin_angular_momentum")],
            # 自旋→磁矩: 电子自旋产生磁偶极矩
            # 这是 QM→EM 的第二条桥 (第一条是光电效应)
        ))
        self.register(PhysicsLaw(
            name="SpinStatistics", domain="quantum",
            latex=r"\psi(x_1,x_2) = \pm \psi(x_2,x_1)",
            inputs=["spin_angular_momentum"], outputs=["occupation_limit"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda spin: 1.0 if spin > 0 else -1.0,
            causal_direction=[("spin_angular_momentum", "occupation_limit")],
            forbidden_directions=[("occupation_limit", "spin_angular_momentum")],
            # 自旋统计: 半整数自旋→费米子(不相容), 整数自旋→玻色子
            # 与 PauliExclusion 互补
        ))
        # ── LQG: 自旋→空间量子 (论文摄入) ──
        self.register(PhysicsLaw(
            name="SpinNetworkGeometry", domain="unification",
            latex=r"\text{spin network} \rightarrow \text{quantized geometry}",
            inputs=["spin_angular_momentum"], outputs=["spacetime_quanta"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda spin: spin * 1.6e-35,  # Planck scale
            causal_direction=[("spin_angular_momentum", "spacetime_quanta")],
            forbidden_directions=[("spacetime_quanta", "spin_angular_momentum")],
            # Loop Quantum Gravity (Rovelli et al.): 自旋网络是空间的量子化单元
            # spin → 面积/体积量子 → 时空在 Planck 尺度是离散的
            # 这是"mass 缺席 quantum"缺口的部分填充: QM(spin) → GR(geometry)
            # tier 2: 主流理论, 数学自洽但未实验证实
        ))
        # ── 纠缠: 量子→信息桥 ──
        self.register(PhysicsLaw(
            name="QuantumEntanglement", domain="quantum",
            latex=r"|\Psi\rangle_{AB} \neq |\psi\rangle_A \otimes |\phi\rangle_B",
            inputs=["wave_function"], outputs=["entangled_state"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda wave_function: 0.5,
            causal_direction=[("wave_function", "entangled_state")],
            forbidden_directions=[("entangled_state", "wave_function")],
            # 量子纠缠: 复合系统的波函数不能分解为子系统波函数的张量积
            # 纠缠产生非局域关联 → 量子信息 → measurement_outcome
        ))
        self.register(PhysicsLaw(
            name="EntanglementEntropy", domain="quantum",
            latex=r"S_A = -\text{Tr}(\rho_A \ln \rho_A)",
            inputs=["entangled_state"], outputs=["information_erased"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda entangled_state: entangled_state * 10.0,
            causal_direction=[("entangled_state", "information_erased")],
            forbidden_directions=[("information_erased", "entangled_state")],
            # 纠缠熵: 纠缠态 → 信息丢失 (部分迹后子系统熵)
            # 连接量子纠缠到 Landauer 原理: 信息→熵
        ))
        # ── ER=EPR: 纠缠→几何桥 (论文摄入) ──
        self.register(PhysicsLaw(
            name="ER_EPR", domain="unification",
            latex=r"\text{entanglement} \Rightarrow \text{wormhole}",
            inputs=["entangled_state"], outputs=["wormhole_geometry"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda entangled_state: entangled_state * 0.5,
            causal_direction=[("entangled_state", "wormhole_geometry")],
            forbidden_directions=[("wormhole_geometry", "entangled_state")],
            # ER=EPR (Maldacena & Susskind 2013): 量子纠缠 = 虫洞几何
            # QM(entanglement) ↔ GR(geometry) 的最深层桥接
            # 来源: arXiv:1412.8483, tier 2 (主流理论, 未实验证实)
        ))
        # ── AdS/CFT: 全息原理 (论文摄入) ──
        self.register(PhysicsLaw(
            name="AdS_CFT", domain="unification",
            latex=r"\mathcal{Z}_{\text{CFT}} = \mathcal{Z}_{\text{gravity}}",
            inputs=["boundary_field"], outputs=["bulk_metric"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda boundary_field: boundary_field * 0.1,
            causal_direction=[("boundary_field", "bulk_metric")],
            forbidden_directions=[("bulk_metric", "boundary_field")],
            # AdS/CFT (Maldacena 1997): 边界共形场论 = 体时空引力
            # 全息原理: 低维边界编码了高维体时空的全部信息
            # 来源: hep-th/9711200, tier 2 (理论确认, 未直接实验证实)
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
        self.register(PhysicsLaw(
            name="MeasurementPostulate", domain="quantum",
            latex=r"\text{Â}|\psi\rangle \rightarrow a_n; P=|\langle\psi_n|\psi\rangle|^2; |\psi\rangle\rightarrow|\psi_n\rangle",
            inputs=["measurement", "wave_function"],
            outputs=["eigenvalue", "post_measurement_state"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda measurement, wave_function: measurement * wave_function if wave_function != 0 else 0.0,
            causal_direction=[
                ("measurement", "eigenvalue"),
                ("wave_function", "eigenvalue"),
                ("measurement", "post_measurement_state"),
            ],
            forbidden_directions=[
                ("eigenvalue", "measurement"),
                ("post_measurement_state", "wave_function"),
            ],
            collapse_timescale="instantaneous (postulate)",
            # 测量公设 (哥本哈根): 坍缩是瞬时的 — 这是公设，不推导，不计时
        ))
        self.register(PhysicsLaw(
            name="ObjectiveCollapse", domain="quantum",
            latex=r"P_{\text{collapse}} = 1 - e^{-\lambda t}",
            inputs=["particle_count", "time"],
            outputs=["collapse_probability"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda particle_count, time, lam=1e-16: 1 - np.exp(-particle_count * lam * time),
            causal_direction=[
                ("particle_count", "collapse_probability"),
                ("time", "collapse_probability"),
            ],
            forbidden_directions=[
                ("collapse_probability", "particle_count"),
            ],
            collapse_timescale="stochastic (rate λ)",
            # 客观坍缩 (GRW/CSL): 自发局域化速率 λ ≈ 10⁻¹⁶ s⁻¹ (单粒子)
            # 宏观物体: N 个粒子 → 有效速率 Nλ → 坍缩时间 ~ 1/(Nλ)
            # 单粒子几乎从不自发坍缩，宏观物体在微秒级坍缩
        ))
        self.register(PhysicsLaw(
            name="VacuumFluctuation", domain="quantum",
            latex=r"\langle 0 | T\{\phi(x)\phi(y)\} | 0 \rangle \neq 0",
            inputs=["vacuum"], outputs=["virtual_particles"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda vacuum=1.0: 0.5,
            causal_direction=[("vacuum", "virtual_particles")],
            forbidden_directions=[],
            # 真空涨落: 真空不是空的 — 虚粒子对不断产生湮灭
            # Casimir 效应、Lamb 移位 的实验证实
            # 真空有结构 — 这是量子场论最深刻的发现之一
        ))
        self.register(PhysicsLaw(
            name="Decoherence", domain="quantum",
            latex=r"\rho_{ij}(t) = \rho_{ij}(0) e^{-\gamma t}",
            inputs=["environment_coupling", "time"],
            outputs=["mixed_state"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda environment_coupling, time: np.exp(-environment_coupling * time),
            causal_direction=[
                ("environment_coupling", "mixed_state"),
                ("time", "mixed_state"),
            ],
            forbidden_directions=[
                ("mixed_state", "environment_coupling"),
            ],
            collapse_timescale="finite (~1/γ)",
            # 退相干: 环境耦合 → 非对角元指数衰减 → 对角密度矩阵 (混合态)
            # 注意: 混合态 ≠ 本征态。退相干解释了为什么干涉项消失，
            # 但不解释为什么观测者只看到一个确定结果。混合态仍是概率集合。
            # 从混合态到单一结果的跳跃需要额外假设:
            #   多世界 (分支)、客观坍缩 (GRW/CSL)、或哥本哈根 (坍缩公设原语)
        ))
        # Kaluza-Klein 约化: 高维测地线 → 低维力
        self.register(PhysicsLaw(
            name="KaluzaKlein", domain="unification",
            latex=r"g_{MN}^{(5)} \rightarrow g_{\mu\nu}^{(4)} + A_\mu + \phi",
            inputs=["higher_d_metric", "compact_dimension"],
            outputs=["4d_metric", "gauge_field", "scalar_field"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda higher_d_metric, compact_dimension: higher_d_metric / (compact_dimension + 1),
            causal_direction=[
                ("higher_d_metric", "gauge_field"),
                ("compact_dimension", "gauge_field"),
                ("higher_d_metric", "4d_metric"),
            ],
            forbidden_directions=[
                ("gauge_field", "higher_d_metric"),
            ],
            # Kaluza-Klein: 5D 时空中的纯测地线运动
            # 投影到 4D 后分解为: 引力 (g_μν) + 电磁力 (A_μ, 规范场) + 标量场 (φ)
            # 5D 的"直线" = 4D 中受洛伦兹力的带电粒子轨迹
            # 这就是"高维直线→低维投影=最小作用量轨迹"的精确数学实现
        ))
        self.register(PhysicsLaw(
            name="GaugeGeometry", domain="unification",
            latex=r"B = \nabla \times A_\mu",
            inputs=["gauge_field"], outputs=["magnetic_field"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda gauge_field: gauge_field * 0.1,
            causal_direction=[("gauge_field", "magnetic_field")],
            forbidden_directions=[("magnetic_field", "gauge_field")],
            # 规范几何: 规范场 A_μ (Kaluza-Klein 中第5维度规分量) → 磁场 B = ∇×A
            # 这是 Kaluza 统一的核心: 高维几何 → 规范场 → 电磁力
            # magnetic_field 已连接 Lorentz 力: magnetic_field → lorentz_force
            # 完整链条: 5D metric → gauge_field → magnetic_field → lorentz_force
        ))
        # ── 广义相对论 ──
        self.register(PhysicsLaw(
            name="EinsteinFieldEq", domain="general_relativity",
            latex=r"G_{\mu\nu} = \frac{8\pi G}{c^4} T_{\mu\nu}",
            inputs=["mass"], outputs=["spacetime_curvature"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda mass, G=6.67e-11, c=3e8: 8 * 3.14159 * G * mass / c**4,
            causal_direction=[("mass", "spacetime_curvature")],
            forbidden_directions=[("spacetime_curvature", "mass")],
            # 爱因斯坦场方程: 质能 (T_μν) → 时空曲率 (G_μν)
            # 物质告诉时空如何弯曲 — GR 的核心方程
        ))
        self.register(PhysicsLaw(
            name="GeodesicDeviation", domain="general_relativity",
            latex=r"\frac{D^2\xi^\mu}{d\tau^2} = -R^\mu_{\alpha\beta\gamma}u^\alpha\xi^\beta u^\gamma",
            inputs=["spacetime_curvature"], outputs=["tidal_force"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda spacetime_curvature: spacetime_curvature * 0.1,
            causal_direction=[("spacetime_curvature", "tidal_force")],
            forbidden_directions=[("tidal_force", "spacetime_curvature")],
            # 测地线偏离: 曲率 → 相邻测地线的相对加速度 = 潮汐力
            # 曲率不只是抽象几何, 它产生可测量的物理效应
        ))
        self.register(PhysicsLaw(
            name="HawkingRadiation", domain="general_relativity",
            latex=r"T_H = \frac{\hbar c^3}{8\pi G M k_B}",
            inputs=["spacetime_curvature"], outputs=["particle_creation"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda spacetime_curvature: spacetime_curvature * 1e-3,
            causal_direction=[("spacetime_curvature", "particle_creation")],
            forbidden_directions=[("particle_creation", "spacetime_curvature")],
            # 霍金辐射: 时空曲率 → 粒子产生 (黑洞蒸发)
            # GR + QFT 的统一 — 曲率可以创造物质
            # 这是几何与量子场论最深刻的交汇点之一
        ))
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
            name="GeodesicEquation", domain="general_relativity",
            latex=r"\frac{d^2 x^\mu}{d\tau^2} + \Gamma^\mu_{\alpha\beta}\frac{dx^\alpha}{d\tau}\frac{dx^\beta}{d\tau} = 0",
            inputs=["schwarzschild_radius"], outputs=["geodesic_path"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda schwarzschild_radius, c=3e8: schwarzschild_radius * c,
            causal_direction=[("schwarzschild_radius", "geodesic_path")],
            forbidden_directions=[("geodesic_path", "schwarzschild_radius")],
            # 测地线方程: 时空曲率 (Christoffel 符号 Γ, 由度规决定) → 自由粒子沿测地线运动
            # schwarzschild_radius 是曲率的度量 → 决定该区域粒子如何运动
            # 这是 GR 的核心: 物质告诉时空如何弯曲, 时空告诉物质如何运动
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
        self.register(PhysicsLaw(
            name="SpacetimeWavelength", domain="unification",
            latex=r"\lambda_{\text{eff}} = \lambda_{\text{flat}} \cdot f(g_{\mu\nu})",
            inputs=["geodesic_path"], outputs=["wavelength"],
            constraint_type=ConstraintType.SCM_EQUATION,
            formula=lambda geodesic_path, hbar=1.0, m=1.0: hbar / (m * (1.0 + 0.01 * abs(hash(str(geodesic_path)) % 100))),
            causal_direction=[("geodesic_path", "wavelength")],
            forbidden_directions=[("wavelength", "geodesic_path")],
            # 时空波长: 局域时空几何 (测地线结构) 决定粒子的有效 de Broglie 波长。
            # 平坦时空还原 λ=h/p; 弯曲时空中波长被度规修正。
            # 这是 de Broglie 关系的几何化 — 波长不是粒子的内在属性, 而是空间结构的属性。
            # 双缝干涉: 缝板 (物质) → 改变空间几何 → 改变有效波长 → 干涉图案。
        ))

        # ── 置信层级赋值 ──
        # 防止未经验证的假说污染因果推理
        TIER_ASSIGNMENTS = {
            # 层级 0 — 公理
            0: ["Newton II", "Newton III", "Hooke", "ConservationEnergy",
                "ConservationMomentum", "EntropyIncrease", "Coulomb",
                "Ohm", "LeastAction", "NoetherTheorem",
                "Ideal Gas", "Kinetic Theory", "Archimedes", "Bernoulli"],
            # 层级 2 — 主流理论 (未100%确证但广泛接受)
            2: ["Decoherence", "Inflation", "HiggsMechanism",
                "ER_EPR", "SpinNetworkGeometry", "AdS_CFT"],
            # 层级 3 — 严肃假说
            3: ["ObjectiveCollapse"],
            # 层级 4 — 探索性编码
            4: ["SpacetimeWavelength"],
        }
        for tier, names in TIER_ASSIGNMENTS.items():
            for law in self._laws:
                if law.name in names:
                    law.confidence_tier = tier

        # ── 负向约束补全: 为缺少 forbidden 的定律添加禁止方向 ──
        FORBIDDEN_ASSIGNMENTS = {
            "Ampere": [("magnetic_field", "current")],
            "Convergence_geodesic_path": [("geodesic_path", "kinetic_energy"), ("geodesic_path", "energy")],
            "Coulomb": [("force_electric", "q1"), ("force_electric", "q2")],
            "Gravity": [("force_gravity", "m1"), ("force_gravity", "m2")],
            "Kinetic Energy": [("kinetic_energy", "mass"), ("kinetic_energy", "velocity")],
            "Lens": [("image_distance", "object_distance")],
            "PauliExclusion": [("occupation_limit", "quantum_state")],
            "Poiseuille": [("flow_rate", "pressure_diff")],
            "VacuumFluctuation": [("virtual_particles", "vacuum")],
            "WaveSpeed": [("wave_speed", "wavelength"), ("wave_speed", "frequency")],
            "Simple Harmonic": [("period", "k"), ("period", "mass")],
            "Pendulum Period": [("period", "length"), ("period", "g")],
            "Faraday": [("induced_emf", "magnetic_flux_change")],
            "Kepler III": [("orbital_period", "orbital_radius")],
            "Doppler": [("observed_frequency", "source_frequency")],
            "Photoelectric": [("kinetic_energy", "frequency")],
            "BornRule": [("probability", "wave_function")],
        }
        for name, forbiddens in FORBIDDEN_ASSIGNMENTS.items():
            for law in self._laws:
                if law.name == name and not law.forbidden_directions:
                    law.forbidden_directions = [tuple(f) for f in forbiddens]


# ── 变量本体论: 分类所有变量 ──
VARIABLE_CLASSIFICATION = {
    "fundamental": {
        "mass", "energy", "time", "momentum", "charge",
        "force", "velocity", "temperature", "frequency",
        "wavelength", "current", "voltage",
    },
    "geometric": {
        "geodesic_path", "spacetime_curvature", "schwarzschild_radius",
        "4d_metric", "higher_d_metric", "tidal_force", "gauge_field",
        "compact_dimension", "scalar_field",
    },
    "quantum": {
        "wave_function", "quantum_amplitude", "collapse_probability",
        "eigenvalue", "post_measurement_state", "mixed_state",
        "virtual_particles",
    },
    "derived": {
        "kinetic_energy", "pressure", "volume", "density",
        "flow_rate", "wave_speed", "dilated_time", "frequency_shift",
        "lorentz_force", "magnetic_field", "force_gravity",
        "force_electric", "induced_emf", "buoyant_force",
        "radiated_power", "particle_creation",
    },
}


def classify_variable(var: str) -> str:
    """返回变量的本体分类"""
    for category, varset in VARIABLE_CLASSIFICATION.items():
        if var.lower() in {v.lower() for v in varset}:
            return category
    return "derived"


def fundamental_variables() -> set:
    return VARIABLE_CLASSIFICATION["fundamental"]


# 全局单例
library = PhysicsLibrary()

# 加载持久化的自学习定律
import json as _json, os as _os
_AUTO_LAWS_FILE = _os.path.expanduser("~/.hermes/physcausal_auto_laws.json")
if _os.path.exists(_AUTO_LAWS_FILE):
    try:
        with open(_AUTO_LAWS_FILE) as _f:
            _auto_laws = _json.load(_f)
        for _al in _auto_laws:
            try:
                law = PhysicsLaw(
                    name=_al["name"], domain=_al.get("domain", "auto"),
                    latex=_al.get("latex", ""),
                    inputs=_al.get("inputs", []),
                    outputs=_al.get("outputs", []),
                    constraint_type=ConstraintType.SCM_EQUATION,
                    formula=lambda *args: 0.0,
                    causal_direction=[tuple(d) for d in _al.get("causal_direction", [])],
                    forbidden_directions=[],
                )
                law._auto_learned = True
                if _al.get("_chain_discovered"):
                    law._chain_discovered = True
                if _al.get("_discovery_note"):
                    law._discovery_note = _al["_discovery_note"]
                law.confidence_tier = _al.get("confidence_tier", 4)
                library.register(law)
            except Exception:
                pass
    except Exception:
        pass
