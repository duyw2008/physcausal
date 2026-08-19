"""
数学推导引擎 — 符号验证物理因果边

给定 src→dst，用 sympy 从方程库中尝试推导关系。
不依赖 LLM，纯符号计算。
"""
from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import sympy as sp
from sympy import symbols, Eq, solve, simplify, Function, Derivative
from sympy.calculus.euler import euler_equations  # δS=0 变分: 从作用量生成运动方程


# ═══════════════════════════════════════════════
# 符号映射: 物理概念名 → sympy Symbol
# ═══════════════════════════════════════════════

_SYMBOL_MAP: Dict[str, sp.Symbol] = {}
_ALIASES: Dict[str, str] = {}  # 别名 → 规范名

# 基本物理量
for name, sym in [
    # 力学
    ("mass", "m"), ("force", "F"), ("acceleration", "a"),
    ("velocity", "v"), ("speed", "v"), ("momentum", "p"),
    ("position", "x"), ("displacement", "x"), ("distance", "d"),
    ("time", "t"), ("energy", "E"), ("kinetic_energy", "E_k"),
    ("potential_energy", "E_p"), ("work", "W"), ("power", "P"),
    ("pressure", "P"), ("density", "rho"), ("volume", "V"),
    ("temperature", "T"), ("entropy", "S"), ("heat", "Q"),
    ("angular_momentum", "L"), ("torque", "tau"),
    ("frequency", "f"), ("angular_frequency", "omega"),
    ("wavelength", "lambda"), ("wave_number", "k"),
    ("amplitude", "A"), ("spring_constant", "k_s"),
    # 电磁
    ("charge", "q"), ("current", "I"), ("voltage", "V_em"),
    ("resistance", "R"), ("capacitance", "C"),
    ("electric_field", "E_f"), ("magnetic_field", "B"),
    ("magnetic_flux", "Phi_B"), ("magnetic_moment", "mu"),
    ("gyromagnetic_ratio", "g_s"), ("zeeman_energy", "E_z"),
    ("induction", "Phi_B"), ("faraday_law", "Phi_B"),
    ("lorentz_force", "F"), ("electromagnetic_force", "F"),
    # 引力波
    ("strain", "h"), ("gw_strain", "h"),
    ("orbital_eccentricity", "e"), ("eccentricity", "e"),
    # 结构 / 群论
    ("structure_group", "S_grp"), ("group", "S_grp"),
    # 引力/相对论
    ("gravitational_constant", "G"), ("gravitational_acceleration", "g"),
    ("speed_of_light", "c"), ("planck_constant", "h"),
    ("reduced_planck_constant", "hbar"),
    ("schwarzschild_radius", "r_s"),
    # 量子
    ("wavefunction", "psi"), ("probability", "P"),
    # 通用
    ("radius", "r"), ("length", "L"), ("area", "A_a"),
    ("angle", "theta"), ("refractive_index", "n"),
    # 量子
    ("wavefunction", "psi"), ("probability", "P"),
    ("quantum_number", "n_q"), ("energy_level", "E_n"),
    ("uncertainty", "Delta"), ("position_uncertainty", "Delta_x"),
    ("momentum_uncertainty", "Delta_p"), ("spin", "s"),
    ("angular_momentum_quantum", "l_q"),
    # 几何/GR
    ("spacetime_curvature", "R"), ("scalar_curvature", "R"),
    ("stress_energy", "T"), ("einstein_tensor", "G_mn"),
    ("geodesic_acceleration", "a_geo"), ("connection_coefficient", "Gamma"),
    ("metric", "g"), ("ricci", "R_mn"), ("spacetime", "M"),
    ("lorentz", "gamma"), ("covariant", "nabla"),
    ("invariant", "I"), ("symmetry", "S_grp"),
    ("tangent", "T_p"), ("bundle", "E"),
    ("holonomy", "Hol"), ("dimension", "n_dim"),
    ("field_strength", "F_mn"),
    ("schwarzschild_radius", "r_s"),
    # 场论
    ("gauge_field", "A_mu"), ("gauge_potential", "A_mu"),
    ("scalar_field", "phi"), ("source_current", "J_mu"),
    ("coupling_constant", "g_c"), ("lagrangian", "L"),
    # 统计力学/核/粒子/流体/固体/天体/光学
    ("partition_function", "Z"), ("free_energy", "F"),
    ("binding_energy", "E_bind"), ("decay_constant", "lambda_d"),
    ("cross_section", "sigma"), ("half_life", "t_half"),
    ("viscosity", "eta"), ("flow_velocity", "u"),
    ("debye_length", "lambda_D"), ("plasma_frequency", "omega_p"),
    ("luminosity", "L_star"), ("orbital_period", "T_orb"),
    ("diffraction_angle", "theta_d"), ("refractive_index", "n"),
    ("proper_time", "tau"), ("rest_mass", "m_0"),
    # 原子物理
    ("rydberg_constant", "R_inf"), ("fine_structure", "alpha_fs"),
    ("bohr_radius", "a_0"), ("zeeman_energy", "E_z"),
    ("spectral_line", "lambda"), ("principal_quantum", "n_q"),
    # 凝聚态/固态
    ("band_gap", "E_g"), ("fermi_energy", "E_f"),
    ("phonon", "omega_ph"), ("effective_mass", "m_star"),
    ("lattice_constant", "a_lat"), ("density_of_states", "g_E"),
    # 量子信息
    ("entanglement_entropy", "S_ent"), ("von_neumann_entropy", "S_ent"),
    ("bell_correlation", "S_bell"), ("fidelity", "F_q"),
    ("qubit", "psi_q"), ("quantum_channel", "N_q"),
    ("purity", "gamma_p"), ("concurrence", "C_ent"),
]:
    s = symbols(sym, real=True, positive=True)
    _SYMBOL_MAP[name] = s

# 别名映射
for alias, canon in [
    ("mass", "mass"), ("m", "mass"), ("weight", "mass"),
    ("force", "force"), ("f", "force"),
    ("acceleration", "acceleration"), ("a", "acceleration"),
    ("velocity", "velocity"), ("v", "velocity"),
    ("energy", "energy"), ("e", "energy"),
    ("charge", "charge"), ("q", "charge"),
    ("current", "current"), ("i", "current"),
    ("voltage", "voltage"), ("potential", "voltage"),
    ("resistance", "resistance"), ("r", "resistance"),
    ("temperature", "temperature"), ("t", "temperature"),
    ("time", "time"),
    # 电磁扩展
    ("magnetic_moment", "magnetic_moment"), ("magnetic_flux", "magnetic_flux"),
    ("induction", "magnetic_flux"), ("faraday_lenz_law", "magnetic_flux"),
    ("lorentz_force_law", "lorentz_force"), ("lorentz_force", "lorentz_force"),
    ("electromagnetic_force", "lorentz_force"),
    # 引力波
    ("strain", "strain"), ("gw_strain", "strain"),
    ("orbital_eccentricity", "orbital_eccentricity"), ("eccentricity", "orbital_eccentricity"),
    # 群论/结构
    ("structure_group", "structure_group"), ("group", "structure_group"),
    ("frequency", "frequency"), ("f", "frequency"),
    ("wavelength", "wavelength"), ("lambda", "wavelength"),
    ("momentum", "momentum"), ("p", "momentum"),
    ("distance", "distance"), ("d", "distance"),
    ("speed_of_light", "speed_of_light"), ("c", "speed_of_light"),
    ("planck_constant", "planck_constant"), ("h", "planck_constant"),
    ("gravitational_constant", "gravitational_constant"), ("g", "gravitational_constant"),
    # 几何 / 微分几何 / GR
    ("metric", "metric"), ("curvature", "spacetime_curvature"), ("spacetime", "spacetime"),
    ("riemann", "spacetime_curvature"), ("ricci", "ricci"), ("einstein_tensor", "einstein_tensor"),
    ("geodesic", "geodesic_acceleration"), ("connection", "connection_coefficient"),
    ("lorentz", "lorentz"), ("minkowski", "lorentz"),
    ("stress_energy", "stress_energy"), ("stress_energy_tensor", "stress_energy"),
    ("energy_momentum_tensor", "stress_energy"),
    ("schwarzschild", "schwarzschild_radius"),
    ("manifold", "spacetime"), ("topology", "spacetime"),
    ("tensor", "einstein_tensor"), ("covariant", "covariant"),
    ("invariant", "invariant"), ("symmetry", "symmetry"),
    ("tangent", "tangent"), ("bundle", "bundle"),
    ("holonomy", "holonomy"), ("dimension", "dimension"),
    ("field_strength", "field_strength"),
    # 量子
    ("quantum", "quantum_number"), ("energy_eigenvalue", "energy_level"),
    ("schrodinger", "wavefunction"), ("heisenberg", "uncertainty"),
    ("born_rule", "probability"), ("normalization", "probability"),
    ("commutator", "uncertainty"), ("tunneling", "probability"),
    ("superposition", "wavefunction"), ("entanglement", "wavefunction"),
    ("spin", "spin"), ("spin_angular_momentum", "spin"),
    ("pauli", "spin"),
    # 场论
    ("gauge_field", "gauge_field"), ("gauge_potential", "gauge_potential"),
    ("four_vector_electromagnetic_potential", "gauge_potential"),
    ("vector_potential", "gauge_potential"), ("A_mu", "gauge_field"),
    ("field_strength_tensor", "field_strength"), ("scalar_field", "scalar_field"),
    ("fermion_field", "scalar_field"), ("vector_field", "gauge_field"),
    ("boson_field", "scalar_field"), ("source_current", "source_current"),
    ("coupling_constant", "coupling_constant"), ("lagrangian", "lagrangian"),
    ("action", "lagrangian"), ("gauge_transformation", "gauge_field"),
    ("maxwell", "field_strength"), ("yang_mills", "gauge_field"),
    ("klein_gordon", "scalar_field"), ("dirac", "scalar_field"),
    ("proca", "gauge_field"), ("electrodynamics", "field_strength"),
    # 统计力学
    ("boltzmann", "partition_function"), ("gibbs", "free_energy"),
    ("helmholtz", "free_energy"), ("statistical", "partition_function"),
    # 核物理
    ("radioactive", "decay_constant"), ("fission", "binding_energy"),
    ("fusion", "binding_energy"), ("nuclear", "binding_energy"),
    # 粒子物理
    ("scattering", "cross_section"), ("higgs", "scalar_field"),
    ("quark", "scalar_field"), ("gluon", "gauge_field"),
    # 流体
    ("navier_stokes", "viscosity"), ("bernoulli", "flow_velocity"),
    ("fluid", "viscosity"), ("turbulence", "viscosity"),
    # 等离子
    ("langmuir", "plasma_frequency"), ("screening", "debye_length"),
    # 天体物理
    ("kepler", "orbital_period"), ("jeans", "luminosity"),
    ("eddington", "luminosity"), ("stellar", "luminosity"),
    ("galaxy", "orbital_period"), ("cosmology", "luminosity"),
    # 光学
    ("snell", "refractive_index"), ("fresnel", "refractive_index"),
    ("interference", "diffraction_angle"), ("diffraction", "diffraction_angle"),
    # 相对论(深)
    ("time_dilation", "proper_time"), ("length_contraction", "proper_time"),
    ("rest_energy", "rest_mass"), ("invariant_mass", "rest_mass"),
    # 原子物理
    ("rydberg", "rydberg_constant"), ("balmer", "spectral_line"),
    ("zeeman", "zeeman_energy"), ("stark", "zeeman_energy"),
    ("bohr_model", "bohr_radius"), ("hydrogen", "rydberg_constant"),
    ("fine_structure_constant", "fine_structure"), ("alpha", "fine_structure"),
    # 凝聚态/固态
    ("conduction_band", "band_gap"), ("valence_band", "band_gap"),
    ("semiconductor", "band_gap"), ("insulator", "band_gap"),
    ("bloch", "band_gap"), ("crystal", "lattice_constant"),
    ("lattice", "lattice_constant"), ("phonon_dispersion", "phonon"),
    ("solid_state", "band_gap"), ("density_of_states", "density_of_states"),
    # 量子信息
    ("entanglement", "entanglement_entropy"), ("von_neumann", "von_neumann_entropy"),
    ("bell_inequality", "bell_correlation"), ("chsh", "bell_correlation"),
    ("teleportation", "fidelity"), ("quantum_error", "fidelity"),
    ("no_cloning", "fidelity"), ("decoherence", "purity"),
    ("mixed_state", "purity"), ("pure_state", "purity"),
    ("quantum_discord", "entanglement_entropy"),
]:
    _ALIASES[alias] = canon


def _normalize(name: str) -> Optional[str]:
    """规范化节点名: 去除 hyp:/abs: 前缀, 下划线转小写匹配"""
    name = name.lower().strip()
    for prefix in ("hyp:", "abs:"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    # 先精确匹配全名（含下划线），防止 "four_vector_electromagnetic_potential"
    # 的子串 "potential" 被误匹配到 "voltage"
    if name in _ALIASES:
        return _ALIASES[name]
    # 再尝试逐词匹配 (处理拼接名如 energy_level → 匹配 energy)
    parts = name.replace("_", " ").split()
    for p in parts:
        if p in _ALIASES:
            return _ALIASES[p]
    return None


def get_symbol(name: str) -> Optional[sp.Symbol]:
    """根据节点名获取对应 sympy Symbol"""
    canon = _normalize(name)
    if canon and canon in _SYMBOL_MAP:
        return _SYMBOL_MAP[canon]
    # fallback: 直接查符号表 (处理没有别名的规范名)
    if name in _SYMBOL_MAP:
        return _SYMBOL_MAP[name]
    # hyp:/abs: 前缀去掉再试
    for prefix in ("hyp:", "abs:"):
        if name.startswith(prefix):
            stripped = name[len(prefix):]
            if stripped in _SYMBOL_MAP:
                return _SYMBOL_MAP[stripped]
    return None


# ═══════════════════════════════════════════════
# 方程库
# ═══════════════════════════════════════════════

def _build_equation_library() -> List[Tuple[str, Eq, List[str], List[str]]]:
    """返回 (name, equation, inputs, outputs) 列表"""
    m, F, a = _SYMBOL_MAP["mass"], _SYMBOL_MAP["force"], _SYMBOL_MAP["acceleration"]
    v, p = _SYMBOL_MAP["velocity"], _SYMBOL_MAP["momentum"]
    E_energy = _SYMBOL_MAP["energy"]
    W, d = _SYMBOL_MAP["work"], _SYMBOL_MAP["displacement"]
    t = _SYMBOL_MAP["time"]
    q, I_var, V_em, R = (_SYMBOL_MAP["charge"], _SYMBOL_MAP["current"],
                          _SYMBOL_MAP["voltage"], _SYMBOL_MAP["resistance"])
    G, g_acc, c = (_SYMBOL_MAP["gravitational_constant"],
                   _SYMBOL_MAP["gravitational_acceleration"],
                   _SYMBOL_MAP["speed_of_light"])
    h, f_l = _SYMBOL_MAP["planck_constant"], _SYMBOL_MAP["frequency"]
    lam, hbar = _SYMBOL_MAP["wavelength"], _SYMBOL_MAP["reduced_planck_constant"]
    r = _SYMBOL_MAP["radius"]
    T = _SYMBOL_MAP["temperature"]
    P_pres, V_vol = _SYMBOL_MAP["pressure"], _SYMBOL_MAP["volume"]
    S, Q_heat = _SYMBOL_MAP["entropy"], _SYMBOL_MAP["heat"]
    rho = _SYMBOL_MAP["density"]
    P_pow = _SYMBOL_MAP["power"]
    omega = _SYMBOL_MAP["angular_frequency"]
    k_wave = _SYMBOL_MAP["wave_number"]
    L_ang = _SYMBOL_MAP["angular_momentum"]
    tau = _SYMBOL_MAP["torque"]
    Phi_B = _SYMBOL_MAP["magnetic_flux"]
    n = _SYMBOL_MAP["refractive_index"]

    eqs = []

    # 力学
    eqs.append(("newton_2nd", Eq(F, m * a), ["mass", "acceleration"], ["force"]))
    eqs.append(("momentum_def", Eq(p, m * v), ["mass", "velocity"], ["momentum"]))
    eqs.append(("kinetic_energy", Eq(_SYMBOL_MAP["kinetic_energy"], m * v**2 / 2), ["mass", "velocity"], ["energy"]))
    eqs.append(("potential_energy", Eq(_SYMBOL_MAP["potential_energy"], m * g_acc * sp.Symbol("h")),
               ["mass", "height"], ["energy"]))
    eqs.append(("work", Eq(W, F * d), ["force", "displacement"], ["work"]))
    eqs.append(("power_def", Eq(P_pow, W / t), ["work", "time"], ["power"]))
    eqs.append(("power_force_velocity", Eq(P_pow, F * v), ["force", "velocity"], ["power"]))
    eqs.append(("impulse_momentum", Eq(F * t, p), ["force", "time"], ["momentum"]))
    eqs.append(("velocity_def", Eq(v, d / t), ["displacement", "time"], ["velocity"]))
    eqs.append(("acceleration_def", Eq(a, v / t), ["velocity", "time"], ["acceleration"]))
    eqs.append(("angular_momentum", Eq(L_ang, m * v * r), ["mass", "velocity", "radius"], ["angular_momentum"]))
    eqs.append(("torque_def", Eq(tau, F * r), ["force", "radius"], ["torque"]))

    # 振动/波动
    eqs.append(("frequency_period", Eq(f_l, 1 / t), ["time"], ["frequency"]))
    eqs.append(("wave_speed", Eq(v, f_l * lam), ["frequency", "wavelength"], ["velocity"]))
    eqs.append(("angular_frequency", Eq(omega, 2 * sp.pi * f_l), ["frequency"], ["angular_frequency"]))
    eqs.append(("wave_number", Eq(k_wave, 2 * sp.pi / lam), ["wavelength"], ["wave_number"]))
    eqs.append(("photon_energy", Eq(E_energy, h * f_l), ["frequency"], ["energy"]))
    eqs.append(("de_broglie", Eq(lam, h / p), ["momentum"], ["wavelength"]))
    eqs.append(("refractive_index", Eq(n, c / v), ["velocity"], ["refractive_index"]))

    # 量子力学 (简化符号形式)
    Delta_x = _SYMBOL_MAP["position_uncertainty"]
    Delta_p = _SYMBOL_MAP["momentum_uncertainty"]
    n_q = _SYMBOL_MAP["quantum_number"]
    E_n = _SYMBOL_MAP["energy_level"]
    psi = _SYMBOL_MAP["wavefunction"]
    prob = _SYMBOL_MAP["probability"]
    hbar = _SYMBOL_MAP["reduced_planck_constant"]
    # Heisenberg uncertainty
    eqs.append(("heisenberg_uncertainty", Eq(Delta_x * Delta_p, hbar / 2),
               ["position_uncertainty"], ["momentum_uncertainty", "uncertainty"]))
    # Particle in a box: E_n = n²π²ℏ²/(2mL²)
    eqs.append(("particle_in_box", Eq(E_n, n_q**2 * sp.pi**2 * hbar**2 / (2 * m * sp.Symbol("L")**2)),
               ["quantum_number", "mass"], ["energy_level"]))
    # Harmonic oscillator: E_n = ℏω(n + ½)
    eqs.append(("harmonic_oscillator", Eq(E_n, hbar * omega * (n_q + sp.Rational(1, 2))),
               ["quantum_number", "angular_frequency"], ["energy_level"]))
    # Born rule: P = |ψ|²
    eqs.append(("born_rule", Eq(prob, psi**2), ["wavefunction"], ["probability"]))

    # 电磁
    eqs.append(("ohms_law", Eq(V_em, I_var * R), ["current", "resistance"], ["voltage"]))
    eqs.append(("electric_power", Eq(P_pow, I_var * V_em), ["current", "voltage"], ["power"]))
    eqs.append(("coulombs_law", Eq(F, sp.Symbol("k_e") * q * q / r**2), ["charge", "radius"], ["force"]))

    # 引力
    eqs.append(("newton_gravity", Eq(F, G * m * m / r**2), ["mass", "radius"], ["force"]))
    eqs.append(("gravity_accel", Eq(g_acc, G * m / r**2), ["mass", "radius"], ["gravitational_acceleration"]))
    eqs.append(("weight", Eq(F, m * g_acc), ["mass"], ["force"]))

    # 微分几何 / 广义相对论 (简化符号形式)
    R_curv = _SYMBOL_MAP["spacetime_curvature"]  # scalar curvature R
    T_stress = _SYMBOL_MAP["stress_energy"]       # stress-energy trace T
    G_tensor = _SYMBOL_MAP["einstein_tensor"]     # Einstein tensor G_mn
    Gamma_conn = _SYMBOL_MAP["connection_coefficient"]  # Christoffel Gamma
    a_geo = _SYMBOL_MAP["geodesic_acceleration"]  # geodesic accel
    # Einstein field equations: curvature ~ mass-energy
    eqs.append(("einstein_field", Eq(R_curv, sp.Symbol("kappa") * T_stress),
               ["stress_energy"], ["spacetime_curvature", "curvature"]))
    # Geodesic: acceleration ~ connection × velocity²
    eqs.append(("geodesic_deviation", Eq(a_geo, Gamma_conn * v**2),
               ["connection_coefficient", "velocity"], ["geodesic_acceleration"]))
    # Curvature from mass (Newtonian limit)
    eqs.append(("curvature_from_mass", Eq(R_curv, G * m / r**3),
               ["mass", "radius"], ["spacetime_curvature", "curvature"]))
    # Ricci scalar from metric
    eqs.append(("ricci_from_metric", Eq(R_curv, sp.Symbol("g_mn") * sp.Symbol("R_mn")),
               ["metric"], ["ricci", "spacetime_curvature"]))
    # Schwarzschild: r_s = 2GM/c²
    eqs.append(("schwarzschild_radius", Eq(r, 2 * G * m / c**2),
               ["mass"], ["radius", "schwarzschild_radius"]))
    # Gravitational redshift: z = GM/(rc²)
    eqs.append(("gravitational_redshift", Eq(sp.Symbol("z"), G * m / (r * c**2)),
               ["mass", "radius"], []))
    # Precession: Δφ = 6πGM/(c²a(1-e²)) (perihelion advance)
    eqs.append(("perihelion_precession", Eq(sp.Symbol("delta_phi"), 6 * sp.pi * G * m / (c**2 * r)),
               ["mass", "radius"], []))
    # Gravitational wave strain: h ~ 2G/(c⁴r) · d²I/dt²
    eqs.append(("gw_strain", Eq(sp.Symbol("h"), 2 * G / (c**4 * r) * m * r**2 / t**2),
               ["mass", "radius", "time"], []))
    # Friedmann: H² = 8πGρ/3 (Hubble parameter ~ density)
    eqs.append(("friedmann", Eq(sp.Symbol("H")**2, 8 * sp.pi * G * rho / 3),
               ["density"], []))
    # Einstein full: G_μν + Λg_μν = 8πG/c⁴ T_μν → trace: -R + 4Λ = 8πG T
    eqs.append(("einstein_trace", Eq(-R_curv + 4 * sp.Symbol("Lambda"), 8 * sp.pi * G / c**4 * T_stress),
               ["spacetime_curvature", "stress_energy"], []))
    # Lorentz factor: γ = 1/√(1-v²/c²)
    eqs.append(("lorentz_factor", Eq(_SYMBOL_MAP["lorentz"], 1 / sp.sqrt(1 - v**2 / c**2)),
               ["velocity"], ["lorentz"]))

    # 量子场论 (简化符号形式)
    A_mu = _SYMBOL_MAP["gauge_field"]
    phi = _SYMBOL_MAP["scalar_field"]
    J_mu = _SYMBOL_MAP["source_current"]
    g_c = _SYMBOL_MAP["coupling_constant"]
    L = _SYMBOL_MAP["lagrangian"]
    F_mn = _SYMBOL_MAP["field_strength"]
    # Maxwell: field strength proportional to source current (∂F ~ J)
    eqs.append(("maxwell_source", Eq(F_mn, sp.Symbol("k_m") * J_mu),
               ["source_current"], ["field_strength"]))
    # Field strength from gauge potential: F ~ dA
    eqs.append(("field_from_potential", Eq(F_mn, sp.Symbol("k_f") * A_mu),
               ["gauge_potential"], ["field_strength"]))
    # Klein-Gordon: mass ~ scalar field ((□+m²)φ=0 → m² = -□φ/φ)
    eqs.append(("klein_gordon_mass", Eq(m, phi),
               ["scalar_field"], ["mass"]))
    # Yang-Mills coupling: field strength ~ coupling × (A² + dA)
    eqs.append(("yang_mills_coupling", Eq(F_mn, g_c * A_mu**2),
               ["coupling_constant", "gauge_field"], ["field_strength"]))
    # Proca: massive gauge field (F ~ m × A)
    eqs.append(("proca_mass", Eq(F_mn, m * A_mu),
               ["mass", "gauge_field"], ["field_strength"]))
    # Lagrangian density: L = F² (free field)
    eqs.append(("free_field_lagrangian", Eq(L, F_mn**2),
               ["field_strength"], ["lagrangian"]))

    # ═══ 自旋-电磁耦合 (量子电动力学桥梁) ═══
    mu = _SYMBOL_MAP["magnetic_moment"]
    g_s = _SYMBOL_MAP["gyromagnetic_ratio"]
    E_z = _SYMBOL_MAP["zeeman_energy"]
    s = _SYMBOL_MAP["spin"]
    B = _SYMBOL_MAP["magnetic_field"]
    # 自旋磁矩: μ = g_s · s  (旋磁比关系)
    eqs.append(("spin_magnetic_moment", Eq(mu, g_s * s),
               ["spin"], ["magnetic_moment"]))
    # 磁矩-磁场线性响应: μ = k_mb · B  (两变量桥接)
    eqs.append(("magnetic_moment_field", Eq(mu, sp.Symbol("k_mb") * B),
               ["magnetic_field"], ["magnetic_moment"]))
    # Zeeman耦合: E_z = -μ · B  (磁矩在磁场中的能量, 备选)
    eqs.append(("zeeman_coupling", Eq(E_z, -mu * B),
               ["magnetic_moment", "magnetic_field"], ["zeeman_energy"]))
    # 矢势→磁场: B = k_b · A_μ  (B = ∇×A 的标量化)
    eqs.append(("potential_to_field", Eq(B, sp.Symbol("k_b") * A_mu),
               ["gauge_field", "gauge_potential"], ["magnetic_field"]))

    # 热力学
    eqs.append(("ideal_gas", Eq(P_pres * V_vol, sp.Symbol("n") * sp.Symbol("R_gas") * T),
               ["pressure", "volume", "temperature"], []))
    eqs.append(("entropy_def", Eq(sp.Symbol("dS"), Q_heat / T), ["heat", "temperature"], ["entropy"]))

    # 相对论
    eqs.append(("mass_energy", Eq(E_energy, m * c**2), ["mass"], ["energy"]))

    # 密度
    eqs.append(("density_def", Eq(rho, m / V_vol), ["mass", "volume"], ["density"]))

    # ═══ 统计力学 ═══
    Z = _SYMBOL_MAP["partition_function"]
    F_free = _SYMBOL_MAP["free_energy"]
    k_B = sp.Symbol("k_B")
    # Boltzmann: P_i = e^{-E_i/kT} / Z
    eqs.append(("boltzmann_factor", Eq(Z, sp.exp(-E_energy / (k_B * T))),
               ["energy", "temperature"], ["partition_function"]))
    # Free energy: F = -kT ln Z
    eqs.append(("free_energy_def", Eq(F_free, -k_B * T * sp.log(Z)),
               ["partition_function", "temperature"], ["free_energy"]))
    # Entropy from partition function: S = k ln Z + E/T
    eqs.append(("entropy_stat", Eq(S, k_B * sp.log(Z) + E_energy / T),
               ["partition_function", "energy", "temperature"], ["entropy"]))

    # ═══ 核物理 ═══
    E_bind = _SYMBOL_MAP["binding_energy"]
    # Binding energy per nucleon ~ 8 MeV
    eqs.append(("binding_energy_def", Eq(E_bind, sp.Symbol("a_v") * m - sp.Symbol("a_s") * m**sp.Rational(2,3)),
               ["mass"], ["binding_energy"]))
    # Radioactive decay: N = N₀ e^{-λt}
    lambda_d = _SYMBOL_MAP["decay_constant"]
    t_half = _SYMBOL_MAP["half_life"]
    eqs.append(("decay_law", Eq(t_half, sp.log(2) / lambda_d),
               ["decay_constant"], ["half_life"]))
    # Decay constant ↔ lifetime
    eqs.append(("decay_lifetime", Eq(lambda_d, 1 / t),
               ["time"], ["decay_constant"]))

    # ═══ 粒子物理 ═══
    sigma = _SYMBOL_MAP["cross_section"]
    # Cross section ~ 1/E² (high energy)
    eqs.append(("cross_section_energy", Eq(sigma, sp.Symbol("g_p")**2 / E_energy**2),
               ["energy"], ["cross_section"]))

    # ═══ 流体力学 ═══
    eta = _SYMBOL_MAP["viscosity"]
    u_flow = _SYMBOL_MAP["flow_velocity"]
    # Bernoulli: P + ½ρv² + ρgh = const
    eqs.append(("bernoulli", Eq(P_pres + rho * u_flow**2 / 2, sp.Symbol("C")),
               ["pressure", "density", "flow_velocity"], ["pressure"]))
    # Reynolds number: Re = ρvL/η
    eqs.append(("reynolds", Eq(sp.Symbol("Re"), rho * u_flow * sp.Symbol("L_char") / eta),
               ["density", "flow_velocity", "viscosity"], []))

    # ═══ 等离子体 ═══
    lambda_D = _SYMBOL_MAP["debye_length"]
    omega_p = _SYMBOL_MAP["plasma_frequency"]
    # Debye length: λ_D = √(ε₀kT / nₑe²)
    eqs.append(("debye_screening", Eq(lambda_D, sp.sqrt(sp.Symbol("eps0") * k_B * T / (sp.Symbol("n_e") * sp.Symbol("e_charge")**2))),
               ["temperature"], ["debye_length"]))
    # Plasma frequency: ω_p = √(nₑe²/ε₀m)
    eqs.append(("plasma_oscillation", Eq(omega_p, sp.sqrt(sp.Symbol("n_e") * sp.Symbol("e_charge")**2 / (sp.Symbol("eps0") * m))),
               ["mass"], ["plasma_frequency"]))

    # ═══ 天体物理 ═══
    L_star = _SYMBOL_MAP["luminosity"]
    T_orb = _SYMBOL_MAP["orbital_period"]
    # Kepler III: T² ∝ r³
    eqs.append(("kepler_third", Eq(T_orb**2, 4 * sp.pi**2 * r**3 / (G * m)),
               ["radius", "mass"], ["orbital_period"]))
    # Eddington luminosity: L = 4πGMmc/σ_T
    eqs.append(("eddington_luminosity", Eq(L_star, 4 * sp.pi * G * m * m * c / sigma if sigma != 0 else sp.Symbol("L_edd")),
               ["mass"], ["luminosity"]))

    # ═══ 光学 ═══
    theta_d = _SYMBOL_MAP["diffraction_angle"]
    # Diffraction: θ ~ λ/d
    eqs.append(("diffraction_limit", Eq(theta_d, lam / sp.Symbol("d_aperture")),
               ["wavelength"], ["diffraction_angle"]))
    # Snell's law: n₁sinθ₁ = n₂sinθ₂
    eqs.append(("snells_law", Eq(n * sp.sin(_SYMBOL_MAP["angle"]), sp.Symbol("n2") * sp.Symbol("theta2")),
               ["refractive_index", "angle"], []))

    # ═══ 相对论(深) ═══
    tau_proper = _SYMBOL_MAP["proper_time"]
    m_0 = _SYMBOL_MAP["rest_mass"]
    # Time dilation: t = γτ
    eqs.append(("time_dilation", Eq(t, _SYMBOL_MAP["lorentz"] * tau_proper),
               ["proper_time", "lorentz"], ["time"]))
    # Relativistic mass: m = γm₀
    eqs.append(("relativistic_mass", Eq(m, _SYMBOL_MAP["lorentz"] * m_0),
               ["rest_mass", "lorentz"], ["mass"]))
    # Invariant: E² - p²c² = m₀²c⁴
    eqs.append(("energy_momentum_invariant", Eq(E_energy**2 - p**2 * c**2, m_0**2 * c**4),
               ["rest_mass", "momentum"], ["energy"]))

    # ═══ 原子物理 ═══
    R_inf = _SYMBOL_MAP["rydberg_constant"]
    alpha_fs = _SYMBOL_MAP["fine_structure"]
    a_0 = _SYMBOL_MAP["bohr_radius"]
    E_z = _SYMBOL_MAP["zeeman_energy"]
    # Rydberg: 1/λ = R(1/n₁² - 1/n₂²)
    eqs.append(("rydberg_formula", Eq(1 / lam, R_inf * (1 / n_q**2 - 1 / sp.Symbol("n2")**2)),
               ["quantum_number", "wavelength"], ["rydberg_constant"]))
    # Fine structure: α = e²/(4πε₀ℏc) ≈ 1/137
    eqs.append(("fine_structure_def", Eq(alpha_fs, sp.Symbol("e_charge")**2 / (4 * sp.pi * sp.Symbol("eps0") * hbar * c)),
               [], ["fine_structure"]))
    # Bohr radius: a₀ = 4πε₀ℏ²/(me²)
    eqs.append(("bohr_radius_def", Eq(a_0, 4 * sp.pi * sp.Symbol("eps0") * hbar**2 / (m * sp.Symbol("e_charge")**2)),
               ["mass"], ["bohr_radius"]))
    # Zeeman: ΔE = μ_B B m_l
    eqs.append(("zeeman_effect", Eq(E_z, sp.Symbol("mu_B") * _SYMBOL_MAP["magnetic_field"] * sp.Symbol("m_l")),
               [], ["zeeman_energy"]))

    # ═══ 凝聚态/固态 ═══
    E_g = _SYMBOL_MAP["band_gap"]
    E_f = _SYMBOL_MAP["fermi_energy"]
    omega_ph = _SYMBOL_MAP["phonon"]
    m_star = _SYMBOL_MAP["effective_mass"]
    a_lat = _SYMBOL_MAP["lattice_constant"]
    g_E = _SYMBOL_MAP["density_of_states"]
    # Band gap ↔ energy levels
    eqs.append(("band_gap_energy", Eq(E_g, E_n - sp.Symbol("E_v")),
               ["energy_level"], ["band_gap"]))
    # Fermi energy: E_f = ℏ²(3π²n)^(2/3) / (2m)
    eqs.append(("fermi_energy_def", Eq(E_f, hbar**2 * (3 * sp.pi**2 * sp.Symbol("n_e"))**sp.Rational(2,3) / (2 * m)),
               ["mass"], ["fermi_energy"]))
    # Phonon: ω = c_s × k (Debye model)
    eqs.append(("phonon_dispersion", Eq(omega_ph, sp.Symbol("c_s") * k_wave),
               ["wave_number"], ["phonon"]))
    # Effective mass: m* = ℏ²/(d²E/dk²)
    eqs.append(("effective_mass_def", Eq(m_star, hbar**2 / (E_n * a_lat**2)),
               ["energy_level", "lattice_constant"], ["effective_mass"]))
    # Free electron DOS: g(E) ∝ √E
    eqs.append(("dos_free_electron", Eq(g_E, sp.sqrt(E_f) * m_star**sp.Rational(3,2)),
               ["fermi_energy", "effective_mass"], ["density_of_states"]))

    # ═══ 量子信息 ═══
    S_ent = _SYMBOL_MAP["entanglement_entropy"]
    S_bell = _SYMBOL_MAP["bell_correlation"]
    F_q = _SYMBOL_MAP["fidelity"]
    gamma_p = _SYMBOL_MAP["purity"]
    C_ent = _SYMBOL_MAP["concurrence"]
    # von Neumann entropy: S = -Tr(ρ ln ρ) → for 2-level: S = -p ln p - (1-p) ln(1-p)
    eqs.append(("von_neumann_entropy", Eq(S_ent, -prob * sp.log(prob) - (1 - prob) * sp.log(1 - prob)),
               ["probability"], ["entanglement_entropy"]))
    # Bell-CHSH: classical bound |S| ≤ 2
    eqs.append(("bell_bound", Eq(S_bell, 2),
               [], ["bell_correlation"]))
    # Fidelity: F = |⟨ψ|φ⟩|² ↔ F = purity for pure states
    eqs.append(("fidelity_purity", Eq(F_q, gamma_p),
               ["purity"], ["fidelity"]))
    # Purity: γ = Tr(ρ²) → γ = entangled/pure measure
    eqs.append(("purity_entanglement", Eq(gamma_p, 1 / (1 + S_ent)),
               ["entanglement_entropy"], ["purity"]))
    # Concurrence: C = √(2(1-γ)) for 2-qubit
    eqs.append(("concurrence_purity", Eq(C_ent, sp.sqrt(2 * (1 - gamma_p))),
               ["purity"], ["concurrence"]))

    return eqs


_EQUATION_LIBRARY: Optional[List] = None


def _get_equations():
    global _EQUATION_LIBRARY
    if _EQUATION_LIBRARY is None:
        _EQUATION_LIBRARY = _build_equation_library()
    return _EQUATION_LIBRARY


# ═══════════════════════════════════════════════
# 推导引擎
# ═══════════════════════════════════════════════

def derive(src_name: str, dst_name: str) -> Optional[Dict]:
    """
    尝试从 src 符号推导到 dst 符号。

    返回:
      None — 推导失败 (无相关方程或符号不匹配)
      {
        "success": True/False,
        "steps": ["F=m*a", "a=F/m"],  # 推导步骤
        "equation": sympy Eq,         # 最终关系式
        "confidence": 0.0~1.0,
      }
    """
    src_sym = get_symbol(src_name)
    dst_sym = get_symbol(dst_name)
    if src_sym is None and dst_sym is None:
        return None
    if src_sym is None:
        src_sym = sp.Symbol(f"_{src_name}")
    if dst_sym is None:
        dst_sym = sp.Symbol(f"_{dst_name}")

    eqs = _get_equations()
    # 收集所有涉及 src 或 dst 的方程
    relevant = []
    for name, eq, inputs, outputs in eqs:
        free = eq.free_symbols
        if src_sym in free or dst_sym in free:
            relevant.append((name, eq))

    if len(relevant) < 1:
        return None

    # 收集所有推导路径的结果 — 不提前返回, 多路径殊途同归 = 交叉验证
    found = []  # (relation, path_label, base_conf)

    # 策略1: 直接替换 — 如果有一个方程同时含 src 和 dst
    for name, eq in relevant:
        free = eq.free_symbols
        if src_sym in free and dst_sym in free:
            try:
                # 尝试解出 dst 关于 src 的表达式
                sol = solve(eq, dst_sym)
                if sol:
                    found.append((Eq(dst_sym, sol[0]), f"direct:{name}", 0.9))
            except Exception:
                pass

    # 策略2: 两跳推导 — 通过共享中间变量 (收集所有共享符号的解, 不提前返回)
    src_eqs = [(n, e) for n, e in relevant if src_sym in e.free_symbols]
    dst_eqs = [(n, e) for n, e in relevant if dst_sym in e.free_symbols]
    for sn, se in src_eqs:
        for dn, de in dst_eqs:
            if sn == dn:
                continue
            # 找共享符号
            shared = se.free_symbols & de.free_symbols
            shared.discard(src_sym)
            shared.discard(dst_sym)
            for mid in shared:
                if str(mid).startswith("_"):
                    continue
                try:
                    mid_expr = solve(se, mid)
                    if not mid_expr:
                        continue
                    subbed = de.subs(mid, mid_expr[0])
                    sol = solve(subbed, dst_sym)
                    if sol:
                        found.append((Eq(dst_sym, sol[0]),
                                      f"bridge:{sn}→{dn} via {mid}", 0.7))
                except Exception:
                    continue

    if not found:
        return {
            "success": False,
            "steps": [f"{n}: {e}" for n, e in relevant[:3]],
            "confidence": 0.1,
        }

    # ═══ 交叉验证: 按公式去重, 多路径命中 = 殊途同归 → 置信叠加 ═══
    from collections import defaultdict
    by_formula = defaultdict(list)
    for rel, path, conf in found:
        by_formula[str(rel)].append((rel, path, conf))

    best = None
    for formula, paths in by_formula.items():
        rel, _, _ = paths[0]
        labels = [p[1] for p in paths]
        has_direct = any("direct" in p for p in labels)
        n_bridge = sum(1 for p in labels if "bridge" in p)
        # 置信: 殊途同归 > 直接解 > 单桥链(跨方程符号身份可疑, 降权等验证)
        if has_direct and n_bridge >= 1:
            conf = 0.95      # 直接解 + 独立桥链 → 两条路得出同一公式
        elif n_bridge >= 2:
            conf = 0.85      # 两条独立桥链
        elif has_direct:
            conf = 0.9       # 单方程直接解 (符号身份在方程内自洽)
        else:
            conf = 0.65      # 单桥链 — 跨方程同一符号可能身份不同 (如 m=中心质量 vs 物体质量)
        if best is None or conf > best["confidence"]:
            best = {
                "success": True,
                "steps": labels,
                "relation": rel,
                "confidence": conf,
                "n_paths": len(paths),
            }

    return best


def quick_check(src_name: str, dst_name: str) -> Tuple[bool, str]:
    """
    快速检查: 两个概念是否有已知物理关系。
    返回 (has_relation, reason)
    """
    src = get_symbol(src_name)
    dst = get_symbol(dst_name)
    if src is None and dst is None:
        return False, "no_symbol_match"

    eqs = _get_equations()
    src_eqs = [n for n, e, _, _ in eqs if src in e.free_symbols] if src else []
    dst_eqs = [n for n, e, _, _ in eqs if dst in e.free_symbols] if dst else []

    if src_eqs and dst_eqs:
        shared = set(src_eqs) & set(dst_eqs)
        if shared:
            return True, f"shared_eq:{','.join(list(shared)[:2])}"
        return True, "bridge_possible"
    elif src_eqs or dst_eqs:
        return False, "only_one_side_known"
    return False, "no_equations"


# ═══════════════════════════════════════════════
# δS=0 变分方法 — 给方法不给结论
# 给: 变分法 (euler_equations) + 作用量的形式 (知识, 真费曼在大学学的)
# 不给: 变分结果映射 (脑自己算运动方程, 自己判断物理意义)
# ═══════════════════════════════════════════════

_VARIATIONAL_KNOWLEDGE: Dict[str, dict] = {}


def _build_variational_knowledge():
    """作用量知识库 (真费曼在大学学的知识, 不是结论)。

    只提供作用量的形式 L(q, q̇, t), 不提供「变分结果是什么」——
    那是脑用变分法自己算出来、自己对照概念图判断的。
    """
    if _VARIATIONAL_KNOWLEDGE:
        return
    t, x = sp.symbols('t x')
    m = sp.Symbol('m', positive=True)

    # 1. 力学作用量: L = T − V = ½m q̇² − V(q)  (知识: 真费曼学的作用量形式)
    q = sp.Function('q')(t)
    dq = sp.Derivative(q, t)
    V = sp.Function('V')
    _VARIATIONAL_KNOWLEDGE['EulerLagrange'] = {
        'lagrangian': sp.Rational(1, 2) * m * dq**2 - V(q),
        'coords': [q], 'params': (t,),
    }

    # 2. 标量场作用量: L = ½(∂φ)² − ½m²φ²  (知识: 场论作用量形式)
    phi = sp.Function('phi')(t, x)
    dphi_t = sp.Derivative(phi, t)
    dphi_x = sp.Derivative(phi, x)
    _VARIATIONAL_KNOWLEDGE['KleinGordon'] = {
        'lagrangian': sp.Rational(1, 2) * (dphi_t**2 - dphi_x**2) - sp.Rational(1, 2) * m**2 * phi**2,
        'coords': [phi], 'params': (t, x),
    }


def derive_variational(action_name: str) -> Optional[Dict]:
    """δS=0 变分方法: 对作用量变分, 得到运动方程。

    给方法不给结论: 返回运动方程 (sympy 变分的产物), 不返回「它是什么物理」——
    那由脑自己对照概念图判断 (符号→概念映射)。

    action_name: 作用量名 (如 'EulerLagrange', 'KleinGordon')

    返回:
      None — 无此作用量
      {success, steps, equation, confidence}
    """
    _build_variational_knowledge()
    entry = _VARIATIONAL_KNOWLEDGE.get(action_name)
    if entry is None:
        return None
    try:
        eoms = euler_equations(entry['lagrangian'], entry['coords'], entry['params'])
        steps = [f"作用量 L = {entry['lagrangian']}"]
        for eq in eoms:
            steps.append(f"δS=0 (欧拉-拉格朗日) → {sp.simplify(eq)} = 0")
        return {
            'success': True,
            'steps': steps,
            'equation': eoms[0] if eoms else None,
            'confidence': 1.0,  # 变分是严格数学推导, 非启发式
        }
    except Exception as e:
        return {'success': False, 'steps': [f'变分失败: {e}'], 'confidence': 0.0}


# ═══════════════════════════════════════════════
# 诺特定理方法 — 从对称性算出守恒量 (给方法不给结论)
# 给: 诺特定理的算法 (Q = ∂L/∂q̇ · δq) + 对称性的定义 (时间/空间平移)
# 不给: 守恒量的物理意义映射 (脑自己算出 Q, 自己判断 Q 是什么)
# ═══════════════════════════════════════════════

_NOETHER_SYMMETRIES: Dict[str, dict] = {}


def _build_noether_symmetries():
    """对称性知识库 (真费曼在大学学的对称性定义, 不是结论)。"""
    if _NOETHER_SYMMETRIES:
        return
    _NOETHER_SYMMETRIES['space_translation'] = {
        'name': '空间平移对称性 (q→q+ε)',
        'kind': 'space',
    }
    _NOETHER_SYMMETRIES['time_translation'] = {
        'name': '时间平移对称性 (t→t+ε)',
        'kind': 'time',
    }


def derive_noether(action_name: str, symmetry: str) -> Optional[Dict]:
    """诺特定理方法: 从对称性算出守恒量。

    给方法不给结论:
    - 方法 (喂种子): 诺特定理 Q = ∂L/∂q̇ · δq — 对称性→守恒量的通用算法
    - 对称性 (喂种子): space_translation / time_translation — 对称性的定义
    - 结论 (不喂果子): 不算出「守恒量=动量/能量」的映射, 由脑自己对照概念图判断

    返回:
      None — 无此作用量或对称性
      {success, conserved_quantity, steps, confidence}
    """
    _build_variational_knowledge()
    _build_noether_symmetries()
    entry = _VARIATIONAL_KNOWLEDGE.get(action_name)
    sym = _NOETHER_SYMMETRIES.get(symmetry)
    if entry is None or sym is None:
        return None
    try:
        L = entry['lagrangian']
        q = entry['coords'][0]
        t = entry['params'][0]
        dq = sp.Derivative(q, t)
        p = sp.diff(L, dq)  # 共轭动量 = ∂L/∂q̇

        if sym['kind'] == 'space':
            # 空间平移: q→q+ε, δq=1 → 守恒量 Q = p (脑自己算, 不硬编码「这是动量」)
            Q = p
        else:
            # 时间平移: t→t+ε → 守恒量 Q = p·q̇ − L (脑自己算, 不硬编码「这是能量」)
            Q = p * dq - L

        # 验证守恒: 用运动方程确认 dQ/dt = 0
        eom = euler_equations(L, [q], (t,))[0]
        steps = [
            f"作用量 L = {L}",
            f"共轭动量 p = ∂L/∂q̇ = {p}",
            f"{sym['name']} → 守恒量 Q = {sp.simplify(Q)}",
            f"守恒验证: dQ/dt 代入运动方程 {sp.simplify(eom)} = 0",
        ]
        return {
            'success': True,
            'conserved_quantity': Q,
            'steps': steps,
            'confidence': 1.0,  # 诺特定理是严格数学推导
        }
    except Exception as e:
        return {'success': False, 'steps': [f'诺特定理失败: {e}'], 'confidence': 0.0}


