"""
物理定律扩张 — EM/光学/声学/现代物理/相对论/尺度桥接

被 physics/laws.py 的 _register_default_laws() 尾部调用。
"""

from __future__ import annotations
import numpy as np
from physics.laws import PhysicsLaw, ConstraintType


def register_expansion_laws(library) -> int:
    """返回注册的定律数"""
    count = 0

    # ═══════════════════════════════════════════════════════
    # 电磁学扩展 (8)
    # ═══════════════════════════════════════════════════════

    library.register(PhysicsLaw(
        name="Maxwell-Faraday", domain="electromagnetism",
        latex=r"\nabla \times \mathbf{E} = -\frac{\partial \mathbf{B}}{\partial t}",
        inputs=["magnetic_field_change"],
        outputs=["induced_e_field"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda dBdt: -dBdt,
        causal_direction=[("magnetic_field_change", "induced_e_field")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Maxwell-Ampere", domain="electromagnetism",
        latex=r"\nabla \times \mathbf{B} = \mu_0 \mathbf{J} + \mu_0 \epsilon_0 \frac{\partial \mathbf{E}}{\partial t}",
        inputs=["current_density", "e_field_change"],
        outputs=["magnetic_field"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda J, dEdt: J + dEdt,
        causal_direction=[("current_density", "magnetic_field"),
                          ("e_field_change", "magnetic_field")],
    )); count += 1

    library.register(PhysicsLaw(
        name="EM Wave", domain="electromagnetism",
        latex=r"\frac{\partial^2 \mathbf{E}}{\partial t^2} = c^2 \nabla^2 \mathbf{E}",
        inputs=["e_field_oscillation", "magnetic_field_oscillation"],
        outputs=["em_radiation"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda E, B: np.sqrt(E**2 + B**2),
        causal_direction=[("e_field_oscillation", "em_radiation"),
                          ("magnetic_field_oscillation", "em_radiation")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Dipole Radiation", domain="electromagnetism",
        latex=r"P = \frac{\mu_0 p_0^2 \omega^4}{12\pi c}",
        inputs=["dipole_moment", "frequency"],
        outputs=["radiated_power"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda p, f: p**2 * f**4,
        causal_direction=[("dipole_moment", "radiated_power"),
                          ("frequency", "radiated_power")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Gauss-Electric", domain="electromagnetism",
        latex=r"\oint \mathbf{E} \cdot d\mathbf{A} = \frac{Q}{\epsilon_0}",
        inputs=["charge"],
        outputs=["e_field_flux"],
        constraint_type=ConstraintType.CONSERVATION,
        formula=lambda Q: Q,
        causal_direction=[("charge", "e_field_flux")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Gauss-Magnetic", domain="electromagnetism",
        latex=r"\oint \mathbf{B} \cdot d\mathbf{A} = 0",
        inputs=[],
        outputs=["no_magnetic_monopole"],
        constraint_type=ConstraintType.CONSERVATION,
        formula=lambda: 0.0,
        causal_direction=[],
    )); count += 1

    library.register(PhysicsLaw(
        name="Waveguide Cutoff", domain="electromagnetism",
        latex=r"f_c = \frac{c}{2a}",
        inputs=["waveguide_width", "frequency"],
        outputs=["propagation_mode"],
        constraint_type=ConstraintType.BOUNDARY,
        formula=lambda a, f: 1.0 if f > 1.0/(2*a) else 0.0,
        causal_direction=[("waveguide_width", "propagation_mode"),
                          ("frequency", "propagation_mode")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Plasma Frequency", domain="electromagnetism",
        latex=r"\omega_p = \sqrt{\frac{n_e e^2}{\epsilon_0 m_e}}",
        inputs=["electron_density"],
        outputs=["plasma_frequency"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda ne: np.sqrt(ne),
        causal_direction=[("electron_density", "plasma_frequency")],
    )); count += 1

    # ═══════════════════════════════════════════════════════
    # 光学扩展 (6)
    # ═══════════════════════════════════════════════════════

    library.register(PhysicsLaw(
        name="Interference", domain="optics",
        latex=r"I = I_1 + I_2 + 2\sqrt{I_1 I_2}\cos\Delta\phi",
        inputs=["path_difference", "wavelength"],
        outputs=["intensity_pattern"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda dx, wl: np.cos(2*np.pi*dx/wl),
        causal_direction=[("path_difference", "intensity_pattern"),
                          ("wavelength", "intensity_pattern")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Diffraction", domain="optics",
        latex=r"d\sin\theta = m\lambda",
        inputs=["aperture_size", "wavelength"],
        outputs=["diffraction_angle"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda d, wl: np.arcsin(wl/d) if d > wl else np.pi/2,
        causal_direction=[("aperture_size", "diffraction_angle"),
                          ("wavelength", "diffraction_angle")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Polarization-Malus", domain="optics",
        latex=r"I = I_0 \cos^2\theta",
        inputs=["incident_intensity", "polarization_angle"],
        outputs=["transmitted_intensity"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda I0, theta: I0 * np.cos(theta)**2,
        causal_direction=[("incident_intensity", "transmitted_intensity"),
                          ("polarization_angle", "transmitted_intensity")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Brewster", domain="optics",
        latex=r"\theta_B = \arctan(n_2/n_1)",
        inputs=["n1", "n2"],
        outputs=["brewster_angle"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda n1, n2: np.arctan(n2/n1),
        causal_direction=[("n1", "brewster_angle"), ("n2", "brewster_angle")],
    )); count += 1

    library.register(PhysicsLaw(
        name="ThinFilm", domain="optics",
        latex=r"2nd\cos\theta = m\lambda",
        inputs=["film_thickness", "refractive_index", "wavelength"],
        outputs=["interference_color"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda d, n, wl: np.cos(2*np.pi*2*n*d/wl),
        causal_direction=[("film_thickness", "interference_color"),
                          ("refractive_index", "interference_color"),
                          ("wavelength", "interference_color")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Grating", domain="optics",
        latex=r"d(\sin\theta_i + \sin\theta_m) = m\lambda",
        inputs=["groove_spacing", "wavelength"],
        outputs=["diffraction_order"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda d, wl: int(d/wl) if wl > 0 else 0,
        causal_direction=[("groove_spacing", "diffraction_order"),
                          ("wavelength", "diffraction_order")],
    )); count += 1

    # ═══════════════════════════════════════════════════════
    # 声学扩展 (5)
    # ═══════════════════════════════════════════════════════

    library.register(PhysicsLaw(
        name="WaveEquation", domain="acoustics",
        latex=r"\frac{\partial^2 p}{\partial t^2} = c_s^2 \nabla^2 p",
        inputs=["bulk_modulus", "density"],
        outputs=["sound_speed"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda K, rho: np.sqrt(K/rho),
        causal_direction=[("bulk_modulus", "sound_speed"),
                          ("density", "sound_speed")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Resonance-Tube", domain="acoustics",
        latex=r"f_n = n\frac{c}{2L}",
        inputs=["tube_length", "sound_speed"],
        outputs=["resonant_frequency"],
        constraint_type=ConstraintType.BOUNDARY,
        formula=lambda L, c: c/(2*L),
        causal_direction=[("tube_length", "resonant_frequency"),
                          ("sound_speed", "resonant_frequency")],
    )); count += 1

    library.register(PhysicsLaw(
        name="StandingWave", domain="acoustics",
        latex=r"p(x,t) = 2A\cos(kx)\sin(\omega t)",
        inputs=["frequency", "sound_speed"],
        outputs=["node_positions"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda f, c: c/(2*f),
        causal_direction=[("frequency", "node_positions"),
                          ("sound_speed", "node_positions")],
    )); count += 1

    library.register(PhysicsLaw(
        name="SoundLevel", domain="acoustics",
        latex=r"L = 10\log_{10}(I/I_0)",
        inputs=["sound_intensity"],
        outputs=["sound_level_dB"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda I: 10*np.log10(max(I, 1e-12)),
        causal_direction=[("sound_intensity", "sound_level_dB")],
    )); count += 1

    library.register(PhysicsLaw(
        name="AcousticImpedance", domain="acoustics",
        latex=r"Z = \rho c",
        inputs=["density", "sound_speed"],
        outputs=["acoustic_impedance"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda rho, c: rho * c,
        causal_direction=[("density", "acoustic_impedance"),
                          ("sound_speed", "acoustic_impedance")],
    )); count += 1

    # ═══════════════════════════════════════════════════════
    # 现代物理扩展 (6)
    # ═══════════════════════════════════════════════════════

    library.register(PhysicsLaw(
        name="NuclearBinding", domain="modern",
        latex=r"B = a_v A - a_s A^{2/3} - a_c Z(Z-1)/A^{1/3} - a_a (A-2Z)^2/A",
        inputs=["nucleon_count", "proton_count"],
        outputs=["binding_energy"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda A, Z: 15.75*A - 17.8*A**(2/3),
        causal_direction=[("nucleon_count", "binding_energy"),
                          ("proton_count", "binding_energy")],
    )); count += 1

    library.register(PhysicsLaw(
        name="RadioactiveDecay", domain="modern",
        latex=r"N(t) = N_0 e^{-\lambda t}",
        inputs=["half_life", "time"],
        outputs=["remaining_fraction"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda T, t: np.exp(-np.log(2)*t/T),
        causal_direction=[("half_life", "remaining_fraction"),
                          ("time", "remaining_fraction")],
    )); count += 1

    library.register(PhysicsLaw(
        name="BandGap", domain="modern",
        latex=r"E_g = f(\text{crystal})",
        inputs=["crystal_structure"],
        outputs=["energy_gap"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda s: 1.0,
        causal_direction=[("crystal_structure", "energy_gap")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Superconductivity", domain="modern",
        latex=r"T < T_c \Rightarrow R = 0",
        inputs=["temperature", "critical_temperature"],
        outputs=["electrical_resistance"],
        constraint_type=ConstraintType.BOUNDARY,
        formula=lambda T, Tc: 0.0 if T < Tc else 1.0,
        causal_direction=[("temperature", "electrical_resistance"),
                          ("critical_temperature", "electrical_resistance")],
    )); count += 1

    library.register(PhysicsLaw(
        name="ComptonScattering", domain="modern",
        latex=r"\Delta\lambda = \frac{h}{m_e c}(1-\cos\theta)",
        inputs=["scattering_angle"],
        outputs=["wavelength_shift"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda theta: 0.00243*(1-np.cos(theta)),
        causal_direction=[("scattering_angle", "wavelength_shift")],
    )); count += 1

    library.register(PhysicsLaw(
        name="PairProduction", domain="modern",
        latex=r"E_\gamma \geq 2m_e c^2",
        inputs=["photon_energy"],
        outputs=["electron_creation", "positron_creation"],
        constraint_type=ConstraintType.BOUNDARY,
        formula=lambda E: 1.0 if E > 1.022 else 0.0,
        causal_direction=[("photon_energy", "electron_creation"),
                          ("photon_energy", "positron_creation")],
    )); count += 1

    # ═══════════════════════════════════════════════════════
    # 相对论扩展 (4)
    # ═══════════════════════════════════════════════════════

    library.register(PhysicsLaw(
        name="TimeDilation", domain="relativity",
        latex=r"\Delta t = \gamma \Delta t_0",
        inputs=["velocity"],
        outputs=["time_dilation_factor"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda v: 1/np.sqrt(max(1-v**2, 1e-10)) if v < 1 else float('inf'),
        causal_direction=[("velocity", "time_dilation_factor")],
    )); count += 1

    library.register(PhysicsLaw(
        name="LengthContraction", domain="relativity",
        latex=r"L = L_0 / \gamma",
        inputs=["velocity"],
        outputs=["length_contraction_factor"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda v: np.sqrt(max(1-v**2, 1e-10)),
        causal_direction=[("velocity", "length_contraction_factor")],
    )); count += 1

    library.register(PhysicsLaw(
        name="RelativisticEnergy", domain="relativity",
        latex=r"E = \gamma m c^2",
        inputs=["mass", "velocity"],
        outputs=["relativistic_energy"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda m, v: m/np.sqrt(max(1-v**2, 1e-10)),
        causal_direction=[("mass", "relativistic_energy"),
                          ("velocity", "relativistic_energy")],
    )); count += 1

    library.register(PhysicsLaw(
        name="GravitationalRedshift", domain="relativity",
        latex=r"\frac{\Delta\lambda}{\lambda} = \frac{GM}{Rc^2}",
        inputs=["mass", "radius"],
        outputs=["wavelength_shift"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda M, R: M/R if R > 0 else 0,
        causal_direction=[("mass", "wavelength_shift"),
                          ("radius", "wavelength_shift")],
    )); count += 1

    # ═══════════════════════════════════════════════════════
    # QFT / Higgs / 量子补全 (13)
    # ═══════════════════════════════════════════════════════

    library.register(PhysicsLaw(
        name="SchrodingerEq", domain="quantum",
        latex=r"i\hbar\frac{\partial}{\partial t}|\psi\rangle = \hat{H}|\psi\rangle",
        inputs=["hamiltonian"], outputs=["wave_function"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda H, t=1.0: abs(H) * t,
        causal_direction=[("hamiltonian", "wave_function")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Tunneling", domain="quantum",
        latex=r"T \approx e^{-2\kappa d},\ \kappa=\sqrt{2m(V-E)}/\hbar",
        inputs=["barrier_height", "barrier_width"],
        outputs=["transmission_probability"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda V, d, E=1.0, m=1.0:
            np.exp(-2*np.sqrt(max(2*m*(V-E), 0))*d) if V > E else 1.0,
        causal_direction=[("barrier_height", "transmission_probability"),
                          ("barrier_width", "transmission_probability")],
    )); count += 1

    library.register(PhysicsLaw(
        name="SpinOrbit", domain="quantum",
        latex=r"H_{SO} = \frac{1}{2m^2c^2}\frac{1}{r}\frac{dV}{dr}\mathbf{L}\cdot\mathbf{S}",
        inputs=["orbital_angular_momentum", "spin_angular_momentum"],
        outputs=["fine_structure_splitting"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda L, S: L * S * 1e-4,
        causal_direction=[("orbital_angular_momentum", "fine_structure_splitting"),
                          ("spin_angular_momentum", "fine_structure_splitting")],
    )); count += 1

    # ── 规范场论 ──
    library.register(PhysicsLaw(
        name="YangMills", domain="qft",
        latex=r"F_{\mu\nu}^a = \partial_\mu A_\nu^a - \partial_\nu A_\mu^a + gf^{abc}A_\mu^b A_\nu^c",
        inputs=["gauge_field"], outputs=["gauge_self_interaction"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda A: A * A,
        causal_direction=[("gauge_field", "gauge_self_interaction")],
    )); count += 1

    library.register(PhysicsLaw(
        name="RunningCoupling", domain="qft",
        latex=r"\alpha(Q^2) = \frac{\alpha(\mu^2)}{1 - \beta_0\alpha(\mu^2)\ln(Q^2/\mu^2)}",
        inputs=["energy_scale", "bare_coupling"],
        outputs=["effective_coupling"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda Q, alpha0, beta0=0.1, mu=1.0:
            alpha0 / max(1 - beta0*alpha0*np.log(max(Q/mu, 1.01)), 1e-10),
        causal_direction=[("energy_scale", "effective_coupling"),
                          ("bare_coupling", "effective_coupling")],
    )); count += 1

    library.register(PhysicsLaw(
        name="AsymptoticFreedom", domain="qft",
        latex=r"\alpha_s(Q^2) \xrightarrow{Q^2\to\infty} 0",
        inputs=["energy_scale", "gauge_coupling"],
        outputs=["effective_coupling"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda Q, g: g / max(np.log(max(Q, 1.01)), 0.1),
        causal_direction=[("energy_scale", "effective_coupling"),
                          ("gauge_coupling", "effective_coupling")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Confinement", domain="qft",
        latex=r"V(r) \sim \sigma r\ \text{for large } r",
        inputs=["quark_separation"], outputs=["string_tension"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda r, sigma=1.0: sigma * r,
        causal_direction=[("quark_separation", "string_tension")],
        forbidden_directions=[("string_tension", "quark_separation")],
    )); count += 1

    # ── 希格斯机制 ──
    library.register(PhysicsLaw(
        name="SpontaneousSymmetryBreaking", domain="qft",
        latex=r"V(\phi) = -\mu^2|\phi|^2 + \lambda|\phi|^4,\ \langle\phi\rangle = v/\sqrt{2}",
        inputs=["order_parameter"], outputs=["vacuum_expectation_value"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda phi, mu=1.0, lam=0.1: mu / np.sqrt(2*lam),
        causal_direction=[("order_parameter", "vacuum_expectation_value")],
        forbidden_directions=[("vacuum_expectation_value", "order_parameter")],
    )); count += 1

    library.register(PhysicsLaw(
        name="GoldstoneTheorem", domain="qft",
        latex=r"\text{broken generator} \Rightarrow \text{massless Goldstone boson}",
        inputs=["broken_symmetry"], outputs=["goldstone_boson"],
        constraint_type=ConstraintType.CONSERVATION,
        formula=lambda bs: 1.0,
        causal_direction=[("broken_symmetry", "goldstone_boson")],
        forbidden_directions=[("goldstone_boson", "broken_symmetry")],
    )); count += 1

    library.register(PhysicsLaw(
        name="HiggsMechanism", domain="qft",
        latex=r"\text{gauge field eats Goldstone} \Rightarrow m_A = g v",
        inputs=["gauge_coupling", "vacuum_expectation_value"],
        outputs=["gauge_boson_mass"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda g, v: g * v,
        causal_direction=[("gauge_coupling", "gauge_boson_mass"),
                          ("vacuum_expectation_value", "gauge_boson_mass")],
        forbidden_directions=[("gauge_boson_mass", "gauge_coupling")],
    )); count += 1

    library.register(PhysicsLaw(
        name="VEVtoMass", domain="qft",
        latex=r"m_f = y_f v / \sqrt{2}",
        inputs=["vacuum_expectation_value", "yukawa_coupling"],
        outputs=["fermion_mass"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda v, y: y * v / np.sqrt(2),
        causal_direction=[("vacuum_expectation_value", "fermion_mass"),
                          ("yukawa_coupling", "fermion_mass")],
    )); count += 1

    library.register(PhysicsLaw(
        name="BrokenSymmetryToGauge", domain="qft",
        latex=r"\partial_\mu \to D_\mu = \partial_\mu + igA_\mu,\ \langle\phi\rangle\neq 0 \Rightarrow m_A = gv",
        inputs=["broken_symmetry"], outputs=["gauge_coupling"],
        constraint_type=ConstraintType.DAG_EDGE,
        formula=lambda bs: bs,
        causal_direction=[("broken_symmetry", "gauge_coupling")],
        forbidden_directions=[("gauge_coupling", "broken_symmetry")],
    )); count += 1

    # ── 深层因果链: 类空因果性 → 对易关系 → 自旋统计 (Pauli 1940) ──
    # 费米子为什么必须反对称: 类空分离处的因果性要求场算符对易,
    # 而半整数自旋的场若对易则违反正能量/洛伦兹不变 → 必须反对易 → Pauli 不相容
    library.register(PhysicsLaw(
        name="SpacelikeCausalityConstraint", domain="qft",
        latex=r"[O_1(x), O_2(y)] = 0\ \text{for}\ (x-y)^2 < 0\ (\text{causality})",
        inputs=["quantum_field", "spacelike_separation"],
        outputs=["field_commutation_relation"],
        constraint_type=ConstraintType.CONSERVATION,
        formula=lambda qf, ss: 1.0 if ss < 0 else 0.0,  # 类空间隔 → 对易/反对易约束
        causal_direction=[("quantum_field", "field_commutation_relation"),
                          ("spacelike_separation", "field_commutation_relation")],
        forbidden_directions=[("field_commutation_relation", "spacelike_separation")],
        # 因果性的数学表达: 类空分离的可观测量必须对易 (否则信号超光速)
        # 这是量子场论因果结构的公理基础
    )); count += 1

    library.register(PhysicsLaw(
        name="SpinStatisticsTheorem", domain="qft",
        latex=r"\text{half-integer spin} \Rightarrow \text{anticommute} \Rightarrow \text{Pauli exclusion}",
        inputs=["spin_angular_momentum", "field_commutation_relation"],
        outputs=["bose_fermi_statistics", "pauli_exclusion"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda spin, comm: -1.0 if (spin % 1 == 0.5 and comm > 0) else 1.0,
        causal_direction=[("spin_angular_momentum", "bose_fermi_statistics"),
                          ("field_commutation_relation", "bose_fermi_statistics"),
                          ("bose_fermi_statistics", "pauli_exclusion")],
        forbidden_directions=[("bose_fermi_statistics", "spin_angular_momentum")],
        # 自旋-统计定理 (Pauli 1940): 半整数自旋场必须反对易 (费米),
        # 整数自旋场必须对易 (玻色) — 由类空因果性 + 正能量 + 洛伦兹不变推出
        # 补齐 SpinStatistics(quantum域) 缺失的因果枢纽: 对易性约束
    )); count += 1

    # ── 深层因果链: 规范原理 → 规范场 → 相互作用 (Yang-Mills 统一) ──
    # 要求局域规范不变性 → 必须引入规范场 (联络) → 协变导数 → 相互作用
    # 这是所有基本力 (电磁/弱/强) 的统一起源
    library.register(PhysicsLaw(
        name="GaugePrincipleToInteraction", domain="qft",
        latex=r"\text{local gauge invariance} \Rightarrow D_\mu = \partial_\mu + igA_\mu \Rightarrow \text{interaction}",
        inputs=["gauge_symmetry"],
        outputs=["gauge_field"],
        constraint_type=ConstraintType.DAG_EDGE,
        formula=lambda gs: gs,
        causal_direction=[("gauge_symmetry", "gauge_field")],
        forbidden_directions=[("gauge_field", "gauge_symmetry")],
        # 规范原理: 局域对称性要求 → 联络/规范场 (不可约表示)
        # 上游: 希格斯机制的起点 (对称破缺发生在规范场之上)
    )); count += 1

    library.register(PhysicsLaw(
        name="GaugeFieldToInteraction", domain="qft",
        latex=r"A_\mu \text{ couples to matter} \Rightarrow \text{force}",
        inputs=["gauge_field", "matter_field"],
        outputs=["fundamental_interaction"],
        constraint_type=ConstraintType.CONSERVATION,
        formula=lambda af, mf: af * mf,
        causal_direction=[("gauge_field", "fundamental_interaction"),
                          ("matter_field", "fundamental_interaction")],
        forbidden_directions=[("fundamental_interaction", "gauge_field")],
        # 规范场与物质场耦合 → 相互作用 (光子-电子、胶子-夸克、W/Z-费米子)
        # 完整链: gauge_symmetry → gauge_field → interaction (力的统一起源)
    )); count += 1

    # ── 深层因果链: 热力学第二定律 → 时间箭头 ──
    # 熵增 (宏观不可逆) → 时间方向 (过去/未来不对称)
    # 因果性的时间基础: 为什么因果总是过去→未来
    library.register(PhysicsLaw(
        name="SecondLawTimeArrow", domain="thermodynamics",
        latex=r"\Delta S \geq 0 \Rightarrow \text{time arrow}",
        inputs=["entropy_increase"],
        outputs=["time_arrow"],
        constraint_type=ConstraintType.CONSERVATION,
        formula=lambda ds: 1.0 if ds >= 0 else -1.0,
        causal_direction=[("entropy_increase", "time_arrow")],
        forbidden_directions=[("time_arrow", "entropy_increase")],
        # 第二定律: 孤立系统熵不减少 → 宏观时间方向
        # 因果箭头 (过去→未来) 的统计力学起源 (Boltzmann 微观态计数)
    )); count += 1

    # ── 深层因果链: 因果性 + 光速有限 → 光锥 → 信息传播上限 ──
    # 相对论因果结构: 信号不能超光速 → 事件分类 (类空/类时/类光) → 因果序
    library.register(PhysicsLaw(
        name="CausalityLightCone", domain="general_relativity",
        latex=r"(x-y)^2 < 0 \Rightarrow \text{no causal influence}",
        inputs=["spacetime_metric", "signal_speed"],
        outputs=["light_cone_structure"],
        constraint_type=ConstraintType.CONSERVATION,
        formula=lambda metric, sp: 1.0 if sp <= 1.0 else 0.0,
        causal_direction=[("spacetime_metric", "light_cone_structure"),
                          ("signal_speed", "light_cone_structure")],
        forbidden_directions=[("light_cone_structure", "signal_speed")],
        # 光锥: 类时=可因果影响, 类空=不可 (与 SpacelikeCausalityConstraint 互补)
        # 信息传播上限 = 因果性的几何表达
    )); count += 1

    library.register(PhysicsLaw(
        name="LightConeToCausalOrder", domain="general_relativity",
        latex=r"\text{light cone} \Rightarrow \text{causal ordering of events}",
        inputs=["light_cone_structure"],
        outputs=["causal_event_order"],
        constraint_type=ConstraintType.DAG_EDGE,
        formula=lambda lc: lc,
        causal_direction=[("light_cone_structure", "causal_event_order")],
        forbidden_directions=[("causal_event_order", "light_cone_structure")],
        # 光锥结构 → 事件因果序 (过去锥/未来锥) → 相对论因果性
        # 完整链: metric+speed → light_cone → causal_order
    )); count += 1

    # ── 深层因果链: 熵 + 全息原理 → 引力是熵力 (Verlinde) ──
    # 热力学时空: 引力不是基本力, 而是熵力 (信息在时空上的梯度)
    library.register(PhysicsLaw(
        name="EntropicGravity", domain="unification",
        latex=r"\Delta S = 2\pi k_B \frac{m c}{\hbar} \Delta x \Rightarrow F = \frac{G M m}{r^2}",
        inputs=["entropy", "holographic_bound"],
        outputs=["gravity_as_entropic_force"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda s, hb: s * hb,
        causal_direction=[("entropy", "gravity_as_entropic_force"),
                          ("holographic_bound", "gravity_as_entropic_force")],
        forbidden_directions=[("gravity_as_entropic_force", "entropy")],
        # Verlinde (2011): 引力 = 熵力 — 全息原理 + 统计力学推出牛顿引力
        # 深链: microstates → entropy → holographic_bound → gravity (引力热力学起源)
    )); count += 1

    return count
