"""
物理世界加料 v2 — 完整版
A: 公式推导  B: 域模板  C: 粒子物理  D: 宇宙学  E: 量子场论
F: 核物理  G: 统计力学  H: 原子物理  I: 人工智能
J: 凝聚态物理  K: 量子信息  L: 微分几何  M: 线性代数  N: 群论  O: 拓扑  P: 概率论  Q: 抽象代数  R: 范畴论

造物主原则: 只加世界结构，不写大脑行为
持久化: 自动注册到 library，重启后 colony 自动加载
"""
from physics.laws import PhysicsLaw, ConstraintType, library


# ═══════════════════════════════════════════════════════════════
# A+B: 公式推导 + 域模板 (v1 内容，合并)
# ═══════════════════════════════════════════════════════════════

FORMULA_AND_TEMPLATES = [
    # ── Classical Mechanics ──
    PhysicsLaw("Newton II", "classical", r"F = ma",
               ["mass","acceleration"], ["force"], ConstraintType.DAG_EDGE,
               lambda m,a: m*a, [("force","acceleration"),("force","mass")]),
    PhysicsLaw("Momentum", "classical", r"p = mv",
               ["mass","velocity"], ["momentum"], ConstraintType.DAG_EDGE,
               lambda m,v: m*v, [("momentum","mass"),("momentum","velocity")]),
    PhysicsLaw("Kinetic Energy", "classical", r"K = mv^2/2",
               ["mass","velocity"], ["kinetic_energy"], ConstraintType.DAG_EDGE,
               lambda m,v: 0.5*m*v**2, [("velocity","kinetic_energy"),("mass","kinetic_energy")]),
    PhysicsLaw("Work-Energy", "classical", r"W = F·d",
               ["force","displacement"], ["work"], ConstraintType.DAG_EDGE,
               lambda f,d: f*d, [("force","work"),("displacement","work")]),
    PhysicsLaw("Power", "classical", r"P = W/t",
               ["work","time"], ["power"], ConstraintType.DAG_EDGE,
               lambda w,t: w/max(t,1e-10), [("work","power")]),
    PhysicsLaw("Angular Momentum", "classical", r"L = r×p",
               ["position","momentum"], ["angular_momentum"], ConstraintType.DAG_EDGE,
               lambda r,p: r*p, [("momentum","angular_momentum"),("position","angular_momentum")]),
    PhysicsLaw("Hooke", "classical", r"F = -kx",
               ["spring_constant","displacement"], ["force"], ConstraintType.DAG_EDGE,
               lambda k,x: -k*x, [("spring_constant","force"),("displacement","force")]),
    PhysicsLaw("Gravitation", "classical", r"F = Gm₁m₂/r²",
               ["mass","distance"], ["gravitational_force"], ConstraintType.DAG_EDGE,
               lambda m,d: m/max(d**2,1e-10), [("mass","gravitational_force"),("distance","gravitational_force")]),
    PhysicsLaw("Kinematics", "classical", r"x→v→a",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("position","velocity"),("velocity","acceleration")]),
    PhysicsLaw("Force Chain", "classical", r"F→a→v→x",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("force","acceleration"),("acceleration","velocity"),("velocity","position")]),
    PhysicsLaw("Torque", "classical", r"τ = Iα",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("torque","angular_acceleration"),("torque","angular_momentum")]),
    PhysicsLaw("Conservation", "classical", r"d/dt(p,E,L)=0",
               [],[], ConstraintType.CONSERVATION, lambda:1.0,
               [("momentum","conserved"),("energy","conserved"),("angular_momentum","conserved")]),

    # ── Electromagnetism ──
    PhysicsLaw("Ohm", "electromagnetism", r"V=IR",
               ["current","resistance"], ["voltage"], ConstraintType.DAG_EDGE,
               lambda i,r: i*r, [("voltage","current"),("voltage","resistance")]),
    PhysicsLaw("Electric Power", "electromagnetism", r"P=IV",
               ["current","voltage"], ["power"], ConstraintType.DAG_EDGE,
               lambda i,v: i*v, [("current","power"),("voltage","power")]),
    PhysicsLaw("Coulomb", "electromagnetism", r"F=kq₁q₂/r²",
               ["charge","distance"], ["electric_force"], ConstraintType.DAG_EDGE,
               lambda q,d: q/max(d**2,1e-10), [("charge","electric_force"),("distance","electric_force")]),
    PhysicsLaw("Faraday", "electromagnetism", r"ε=-dΦ/dt",
               ["magnetic_flux"], ["induced_emf"], ConstraintType.DAG_EDGE,
               lambda f: -f, [("magnetic_flux","induced_emf")]),
    PhysicsLaw("Capacitance", "electromagnetism", r"C=Q/V",
               ["charge","voltage"], ["capacitance"], ConstraintType.DAG_EDGE,
               lambda q,v: q/max(v,1e-10), [("charge","capacitance"),("voltage","capacitance")]),
    PhysicsLaw("Inductance", "electromagnetism", r"V=L·dI/dt",
               ["current"], ["voltage"], ConstraintType.DAG_EDGE,
               lambda i: i, [("inductance","voltage"),("current","voltage")]),
    PhysicsLaw("Maxwell Struct", "electromagnetism", r"∇·E,∇×B",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("charge","electric_field"),("current","magnetic_field"),
                ("electric_field","magnetic_field"),("magnetic_field","electric_field")]),
    PhysicsLaw("Circuit Laws", "electromagnetism", r"V=IR,P=IV",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("voltage","current"),("current","power"),("resistance","current")]),
    PhysicsLaw("EM Waves", "electromagnetism", r"c=1/√(μ₀ε₀)",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("electric_field","electromagnetic_wave"),("magnetic_field","electromagnetic_wave"),
                ("electromagnetic_wave","photon_energy")]),

    # ── Quantum Mechanics ──
    PhysicsLaw("Planck-Einstein", "quantum", r"E=hν",
               ["frequency"], ["photon_energy"], ConstraintType.DAG_EDGE,
               lambda f: 6.626e-34*f, [("frequency","photon_energy")]),
    PhysicsLaw("De Broglie", "quantum", r"λ=h/p",
               ["momentum"], ["wavelength"], ConstraintType.DAG_EDGE,
               lambda p: 6.626e-34/max(p,1e-30), [("momentum","wavelength")]),
    PhysicsLaw("Heisenberg", "quantum", r"ΔxΔp≥ħ/2",
               ["position_uncertainty"], ["momentum_uncertainty"], ConstraintType.DAG_EDGE,
               lambda x: 1.054e-34/max(x,1e-30), [("position_uncertainty","momentum_uncertainty")]),
    PhysicsLaw("Schrödinger", "quantum", r"iħ∂ψ/∂t=Ĥψ",
               ["hamiltonian","wave_function"], ["energy_eigenvalue"], ConstraintType.DAG_EDGE,
               lambda h,w: h, [("hamiltonian","energy_eigenvalue"),("wave_function","energy_eigenvalue")]),
    PhysicsLaw("Born Rule", "quantum", r"P=|ψ|²",
               ["wave_function"], ["probability"], ConstraintType.DAG_EDGE,
               lambda w: w**2, [("wave_function","probability")]),
    PhysicsLaw("State Evolution", "quantum", r"|ψ⟩→Ĥ→|ψ'⟩",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("hamiltonian","state_vector"),("state_vector","observable"),("observable","measurement")]),
    PhysicsLaw("Spin", "quantum", r"S=ħσ/2",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("spin","magnetic_moment"),("spin","angular_momentum")]),
    PhysicsLaw("Entanglement", "quantum", r"|Ψ⟩≠|ψ⟩⊗|φ⟩",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("entanglement","bell_correlations"),("entanglement","quantum_information")]),
    PhysicsLaw("Measurement", "quantum", r"superpos→meas→eigen",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("superposition","measurement"),("measurement","eigenvalue"),("measurement","probability")]),
    PhysicsLaw("Commutator", "quantum", r"[x,p]=iħ",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("position","momentum_uncertainty"),("momentum","position_uncertainty")],
               forbidden_directions=[("position","momentum")]),

    # ── Thermodynamics ──
    PhysicsLaw("Ideal Gas", "thermodynamics", r"PV=nRT",
               ["pressure","volume","temperature"], ["pressure"], ConstraintType.DAG_EDGE,
               lambda p,v,t: t/max(v,1e-10), [("temperature","pressure"),("volume","pressure")]),
    PhysicsLaw("Boltzmann Entropy", "thermodynamics", r"S=k·lnW",
               ["microstates"], ["entropy"], ConstraintType.DAG_EDGE,
               lambda m: 1.38e-23*__import__('math').log(max(m,1)),
               [("microstates","entropy")]),
    PhysicsLaw("First Law", "thermodynamics", r"ΔU=Q-W",
               ["heat","work"], ["internal_energy"], ConstraintType.DAG_EDGE,
               lambda q,w: q-w, [("heat","internal_energy"),("work","internal_energy")]),
    PhysicsLaw("Heat Capacity", "thermodynamics", r"Q=mcΔT",
               ["mass","temperature"], ["heat"], ConstraintType.DAG_EDGE,
               lambda m,t: m*t, [("mass","heat"),("temperature","heat")]),
    PhysicsLaw("Carnot", "thermodynamics", r"η=1-T_c/T_h",
               ["temperature"], ["efficiency"], ConstraintType.DAG_EDGE,
               lambda t: 1-1/max(t,1), [("temperature","efficiency")]),
    PhysicsLaw("Potentials", "thermodynamics", r"F=U-TS",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("internal_energy","free_energy"),("entropy","free_energy"),
                ("temperature","free_energy"),("free_energy","chemical_potential")]),
    PhysicsLaw("StatMech Bridge", "thermodynamics", r"Z=Σe^{-βE}",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("microstates","partition_function"),("partition_function","free_energy"),
                ("partition_function","entropy"),("partition_function","internal_energy")]),

    # ── Relativity ──
    PhysicsLaw("E=mc²", "relativity", r"E=mc²",
               ["mass"], ["energy"], ConstraintType.DAG_EDGE,
               lambda m: m*9e16, [("mass","energy")]),
    PhysicsLaw("Time Dilation", "relativity", r"Δt'=γΔt",
               ["velocity"], ["time_dilation_factor"], ConstraintType.DAG_EDGE,
               lambda v: 1/max((1-(v/3e8)**2)**0.5,1e-10), [("velocity","time_dilation_factor")]),
    PhysicsLaw("Length Contraction", "relativity", r"L'=L/γ",
               ["velocity"], ["length_contraction_factor"], ConstraintType.DAG_EDGE,
               lambda v: (1-(v/3e8)**2)**0.5, [("velocity","length_contraction_factor")]),
    PhysicsLaw("Einstein Field", "general_relativity", r"G=8πGT/c⁴",
               ["stress_energy_tensor"], ["spacetime_curvature"], ConstraintType.DAG_EDGE,
               lambda s: s, [("stress_energy_tensor","spacetime_curvature")]),
    PhysicsLaw("Spacetime", "general_relativity", r"ds²=g_μνdx^μdx^ν",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("metric_tensor","spacetime_interval"),("spacetime_interval","geodesic"),
                ("geodesic","proper_time")]),
    PhysicsLaw("GR Matter", "general_relativity", r"G=8πGT",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("stress_energy_tensor","spacetime_curvature"),("mass","stress_energy_tensor"),
                ("energy","stress_energy_tensor"),("momentum","stress_energy_tensor")]),
    PhysicsLaw("Relativistic Kin", "relativity", r"γ=1/√(1-v²/c²)",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("velocity","lorentz_factor"),("lorentz_factor","time_dilation"),
                ("lorentz_factor","length_contraction"),("velocity","relativistic_mass")]),

    # ── Optics ──
    PhysicsLaw("Wave Eq", "optics", r"v=fλ",
               ["frequency","wavelength"], ["wave_speed"], ConstraintType.DAG_EDGE,
               lambda f,w: f*w, [("frequency","wave_speed"),("wavelength","wave_speed")]),
    PhysicsLaw("Snell", "optics", r"n₁sinθ₁=n₂sinθ₂",
               ["refractive_index"], ["refraction_angle"], ConstraintType.DAG_EDGE,
               lambda n: n, [("refractive_index","refraction_angle")]),

    # ── Unification Bridges ──
    PhysicsLaw("QM-Classical", "unification", r"⟨Â⟩→A_class",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("wave_function","probability"),("probability","measurement"),
                ("measurement","classical_observable")]),
    PhysicsLaw("GR-QM Tension", "unification", r"G vs Ĥ",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("spacetime_curvature","wave_function"),("energy","spacetime_curvature")],
               forbidden_directions=[("wave_function","spacetime_curvature")]),
    PhysicsLaw("EM-QM Bridge", "unification", r"Ĥ=(p̂-qA)²/2m+qφ",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("electric_field","hamiltonian"),("magnetic_field","hamiltonian"),
                ("hamiltonian","wave_function")]),
    PhysicsLaw("Thermo-QM", "unification", r"ρ=e^{-βĤ}/Z",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("hamiltonian","density_matrix"),("temperature","density_matrix"),
                ("density_matrix","entropy")]),
    PhysicsLaw("GR-Thermo", "unification", r"T_H=ħc³/8πGMk",
               [],[], ConstraintType.DAG_EDGE, lambda:1.0,
               [("mass","hawking_temperature"),("hawking_temperature","entropy")]),
]


# ═══════════════════════════════════════════════════════════════
# C: 粒子物理
# ═══════════════════════════════════════════════════════════════

PARTICLE_PHYSICS = [
    PhysicsLaw("Quark Structure", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("quark","hadron"),("quark","color_charge"),("quark","flavor")]),
    PhysicsLaw("Lepton Family", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("lepton","weak_force"),("lepton","electric_charge"),
                ("lepton","neutrino"),("neutrino","flavor")]),
    PhysicsLaw("Strong Force", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("gluon","color_charge"),("color_charge","strong_force"),
                ("strong_force","confinement"),("strong_force","asymptotic_freedom")]),
    PhysicsLaw("Weak Force", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("weak_force","beta_decay"),("weak_force","neutrino"),
                ("weak_force","flavor"),("weak_force","cp_violation")]),
    PhysicsLaw("Electroweak", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("electroweak","weak_force"),("electroweak","electromagnetic_force"),
                ("electroweak","higgs_field")]),
    PhysicsLaw("Higgs Mechanism", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("higgs_field","higgs_boson"),("higgs_field","mass"),
                ("higgs_boson","mass"),("higgs_mechanism","electroweak")]),
    PhysicsLaw("Confinement", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("confinement","hadron"),("confinement","quark"),
                ("asymptotic_freedom","strong_force")]),
    PhysicsLaw("CP Violation", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("cp_violation","matter_antimatter_asymmetry"),("cp_violation","flavor")]),
    PhysicsLaw("Particle->Nuclear", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("quark","proton"),("quark","neutron"),("gluon","binding_energy")]),
    PhysicsLaw("Particle->Cosmology", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("higgs_field","inflation"),("quark","big_bang_nucleosynthesis"),
                ("cp_violation","matter_antimatter_asymmetry")]),
]

# ═══════════════════════════════════════════════════════════════
# D: 宇宙学
# ═══════════════════════════════════════════════════════════════

COSMOLOGY = [
    PhysicsLaw("Hubble Law", "cosmology", "",
               ["distance"], ["redshift"], ConstraintType.DAG_EDGE,
               lambda d: d, [("distance","redshift"),("hubble_constant","redshift")]),
    PhysicsLaw("Expansion", "cosmology", "",
               ["density","pressure"], ["expansion_rate"], ConstraintType.DAG_EDGE,
               lambda d,p: d, [("density","expansion_rate"),("pressure","expansion_rate")]),
    PhysicsLaw("Dark Sector", "cosmology", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("dark_energy","expansion_rate"),("dark_matter","structure_formation"),
                ("dark_matter","galaxy_rotation")]),
    PhysicsLaw("Inflation", "cosmology", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("inflation","expansion_rate"),("inflation","structure_formation"),
                ("inflation","cosmic_microwave_background")]),
    PhysicsLaw("CMB", "cosmology", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("cosmic_microwave_background","recombination"),
                ("cosmic_microwave_background","baryon_acoustic_oscillation"),
                ("recombination","redshift")]),
    PhysicsLaw("Structure Formation", "cosmology", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("dark_matter","structure_formation"),("baryon_acoustic_oscillation","structure_formation"),
                ("structure_formation","galaxy_cluster")]),
    PhysicsLaw("BBN", "cosmology", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("big_bang_nucleosynthesis","proton"),("big_bang_nucleosynthesis","neutron"),
                ("big_bang_nucleosynthesis","fusion")]),
]

# ═══════════════════════════════════════════════════════════════
# E: 量子场论
# ═══════════════════════════════════════════════════════════════

QFT = [
    PhysicsLaw("Field Quantization", "quantum_field_theory", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("quantum_field","virtual_particle"),("quantum_field","vacuum_fluctuation")]),
    PhysicsLaw("Path Integral", "quantum_field_theory", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("path_integral","quantum_field"),("path_integral","feynman_diagram"),
                ("action","path_integral")]),
    PhysicsLaw("Feynman Rules", "quantum_field_theory", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("feynman_diagram","s_matrix"),("feynman_diagram","virtual_particle"),
                ("s_matrix","cross_section")]),
    PhysicsLaw("Renormalization", "quantum_field_theory", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("renormalization","coupling_constant"),("renormalization","gauge_theory"),
                ("asymptotic_freedom","renormalization")]),
    PhysicsLaw("Gauge Theory", "quantum_field_theory", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("gauge_theory","quantum_field"),("gauge_theory","strong_force"),
                ("gauge_theory","electroweak"),("gauge_theory","propagator")]),
    PhysicsLaw("Vacuum", "quantum_field_theory", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("vacuum_fluctuation","dark_energy"),("vacuum_fluctuation","virtual_particle"),
                ("vacuum_fluctuation","casimir_effect")]),
    PhysicsLaw("QFT->QM", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("quantum_field","wave_function"),("feynman_diagram","probability"),
                ("s_matrix","measurement")]),
    PhysicsLaw("QFT->GR", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("quantum_field","spacetime_curvature"),("graviton","spacetime_curvature")]),
]

# ═══════════════════════════════════════════════════════════════
# F: 核物理
# ═══════════════════════════════════════════════════════════════

NUCLEAR = [
    PhysicsLaw("Nuclear Binding", "nuclear_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("binding_energy","nuclear_stability"),("proton","binding_energy"),
                ("neutron","binding_energy")]),
    PhysicsLaw("Beta Decay", "nuclear_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("neutron","beta_decay"),("beta_decay","proton"),
                ("beta_decay","neutrino"),("weak_force","beta_decay")]),
    PhysicsLaw("Alpha Decay", "nuclear_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("alpha_decay","half_life"),("alpha_decay","binding_energy"),
                ("alpha_decay","nuclear_decay")]),
    PhysicsLaw("Nuclear Fusion", "nuclear_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("fusion","binding_energy"),("fusion","energy"),
                ("fusion","neutron"),("temperature","fusion")]),
    PhysicsLaw("Nuclear Fission", "nuclear_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("fission","binding_energy"),("fission","energy"),
                ("neutron","fission"),("fission","nuclear_decay")]),
    PhysicsLaw("Decay Chain", "nuclear_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("gamma_decay","photon_energy"),("nuclear_decay","half_life")]),
    PhysicsLaw("Nuclear->Astro", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("fusion","stellar_energy"),("fusion","heavy_elements"),
                ("binding_energy","iron_peak")]),
]

# ═══════════════════════════════════════════════════════════════
# G: 统计力学
# ═══════════════════════════════════════════════════════════════

STATMECH = [
    PhysicsLaw("Ensemble Theory", "statistical_mechanics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("ensemble","partition_function"),("ensemble","ergodicity")]),
    PhysicsLaw("Ergodicity", "statistical_mechanics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("ergodicity","ensemble"),("ergodicity","equilibrium")]),
    PhysicsLaw("Phase Transition", "statistical_mechanics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("phase_transition","critical_point"),("phase_transition","order_parameter"),
                ("critical_point","correlation_function"),("correlation_function","fluctuation")]),
    PhysicsLaw("Fluctuation-Dissipation", "statistical_mechanics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("fluctuation","temperature"),("fluctuation","correlation_function")]),
    PhysicsLaw("Spontaneous Symmetry Breaking", "statistical_mechanics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("spontaneous_symmetry_breaking","phase_transition"),
                ("spontaneous_symmetry_breaking","order_parameter"),
                ("spontaneous_symmetry_breaking","higgs_mechanism")]),
    PhysicsLaw("StatMech->Thermo", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("partition_function","free_energy"),("ensemble","entropy"),
                ("phase_transition","critical_point")]),
]

# ═══════════════════════════════════════════════════════════════
# H: 原子物理
# ═══════════════════════════════════════════════════════════════

ATOMIC = [
    PhysicsLaw("Bohr Model", "atomic_physics", "",
               ["principal_quantum_number"], ["energy_level"], ConstraintType.DAG_EDGE,
               lambda n: -13.6/max(n**2,1), [("principal_quantum_number","energy_level")]),
    PhysicsLaw("Atomic Orbitals", "atomic_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("atomic_orbital","electron_shell"),("atomic_orbital","spectral_line"),
                ("electron_shell","ionization_energy")]),
    PhysicsLaw("Fine Structure", "atomic_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("spin","fine_structure"),("fine_structure","spectral_line"),
                ("fine_structure","hyperfine_structure")]),
    PhysicsLaw("Transition Dipole", "atomic_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("transition_dipole","spectral_line"),("transition_dipole","photon_energy"),
                ("wave_function","transition_dipole")]),
    PhysicsLaw("Atomic->QM", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("hamiltonian","energy_level"),("wave_function","atomic_orbital"),
                ("energy_level","spectral_line")]),
]

# ═══════════════════════════════════════════════════════════════
# I: 人工智能
# ═══════════════════════════════════════════════════════════════

AI = [
    PhysicsLaw("Neural Network", "artificial_intelligence", "",
               ["input_data","weights"], ["output"], ConstraintType.DAG_EDGE,
               lambda x,w: x*w, [("input_data","neural_network"),("weights","neural_network"),
               ("neural_network","output")]),
    PhysicsLaw("Deep Learning", "artificial_intelligence", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("neural_network","deep_learning"),("deep_learning","representation"),
                ("deep_learning","feature_extraction")]),
    PhysicsLaw("LLM Architecture", "artificial_intelligence", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("pretraining","large_language_model"),("large_language_model","fine_tuning"),
                ("fine_tuning","prompting"),("prompting","output")]),
    PhysicsLaw("Emergence", "artificial_intelligence", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("large_language_model","emergence"),("emergence","reasoning"),
                ("emergence","in_context_learning")]),
    PhysicsLaw("AI->Physics", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("neural_network","physics_simulation"),("transformer","symbolic_regression"),
                ("reinforcement_learning","experimental_design")]),
    PhysicsLaw("Physics->AI", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("hamiltonian","neural_network"),("symmetry","equivariant_network"),
                ("entropy","loss_function"),("energy","optimization")]),
]

# ═══════════════════════════════════════════════════════════════
# J: 凝聚态物理
# ═══════════════════════════════════════════════════════════════

CONDENSED_MATTER = [
    PhysicsLaw("Band Theory", "condensed_matter", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("crystal_structure","band_structure"),("band_structure","conductor"),
                ("band_structure","insulator"),("band_structure","semiconductor")]),
    PhysicsLaw("Superconductivity", "condensed_matter", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("cooper_pair","superconductivity"),("electron_phonon","cooper_pair"),
                ("superconductivity","meissner_effect")]),
    PhysicsLaw("Magnetism", "condensed_matter", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("spin","magnetic_order"),("magnetic_order","ferromagnetism"),
                ("magnetic_order","antiferromagnetism")]),
]

# ═══════════════════════════════════════════════════════════════
# K: 量子信息
# ═══════════════════════════════════════════════════════════════

QUANTUM_INFORMATION = [
    PhysicsLaw("Qubit", "quantum_information", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("qubit","superposition"),("qubit","entanglement"),
                ("qubit","quantum_gate")]),
    PhysicsLaw("Quantum Circuit", "quantum_information", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("quantum_gate","quantum_circuit"),("quantum_circuit","quantum_algorithm"),
                ("quantum_circuit","quantum_error_correction")]),
    PhysicsLaw("No Cloning", "quantum_information", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("no_cloning_theorem","quantum_key_distribution"),
                ("no_cloning_theorem","quantum_cryptography")]),
]

# ═══════════════════════════════════════════════════════════════
# L: 微分几何
# ═══════════════════════════════════════════════════════════════

GEOMETRY = [
    PhysicsLaw("Manifold", "geometry", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("manifold","tangent_space"),("manifold","metric_tensor"),
                ("manifold","connection")]),
    PhysicsLaw("Curvature", "geometry", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("connection","curvature"),("curvature","riemann_tensor"),
                ("riemann_tensor","ricci_tensor"),("ricci_tensor","scalar_curvature")]),
    PhysicsLaw("Geometry->GR", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("metric_tensor","spacetime_curvature"),("curvature","einstein_hilbert_action"),
                ("connection","covariant_derivative")]),
]

# ═══════════════════════════════════════════════════════════════
# M: 线性代数  N: 群论  O: 拓扑  P: 概率论  Q: 抽象代数  R: 范畴论
# ═══════════════════════════════════════════════════════════════

LINEAR_ALGEBRA = [
    PhysicsLaw("Linear Space", "linear_algebra", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("vector_space","basis"),("vector_space","dimension"),
                ("linear_transformation","matrix")]),
    PhysicsLaw("Eigen", "linear_algebra", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("matrix","eigenvalue"),("matrix","eigenvector"),
                ("eigenvalue","spectral_decomposition")]),
    PhysicsLaw("Inner Product", "linear_algebra", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("inner_product","orthogonality"),("inner_product","norm"),
                ("inner_product","hilbert_space")]),
    PhysicsLaw("Linear->QM", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("hilbert_space","wave_function"),("eigenvalue","energy_eigenvalue"),
                ("matrix","operator"),("spectral_decomposition","measurement")]),
]

# ═══════════════════════════════════════════════════════════════
# N: 群论
# ═══════════════════════════════════════════════════════════════

GROUP_THEORY = [
    PhysicsLaw("Group", "group_theory", "",
               [], ["group","identity","inverse","associativity"], ConstraintType.DAG_EDGE, None,
               [("group","subgroup"),("group","homomorphism"),("group","representation")]),
    PhysicsLaw("Lie Group", "group_theory", "",
               ["group","manifold"], ["lie_group","lie_algebra"], ConstraintType.DAG_EDGE, None,
               [("lie_group","generator"),("lie_algebra","structure_constant"),
                ("lie_group","exponential_map")]),
    PhysicsLaw("Representation Theory", "group_theory", "",
               ["group","vector_space"], ["representation","irreducible_representation","character"], ConstraintType.DAG_EDGE, None,
               [("representation","matrix_group"),("irreducible_representation","selection_rule"),
                ("representation","angular_momentum")]),
    PhysicsLaw("Unitary Groups", "group_theory", "",
               ["lie_group","unitary"], ["SU_N","U_1"], ConstraintType.DAG_EDGE, None,
               [("SU_2","spin"),("SU_3","color_charge"),("U_1","electromagnetic_gauge"),
                ("SU_2","weak_isospin")]),
    PhysicsLaw("Lorentz Group", "group_theory", "",
               ["lie_group","spacetime"], ["lorentz_group","poincare_group"], ConstraintType.DAG_EDGE, None,
               [("lorentz_group","spinor"),("poincare_group","mass_casimir"),
                ("lorentz_group","lorentz_transformation")]),
    PhysicsLaw("Noether Theorem", "group_theory", "",
               ["symmetry","lie_group","action"], ["conserved_quantity","noether_charge"], ConstraintType.DAG_EDGE, None,
               [("continuous_symmetry","conserved_current"),("time_translation","energy"),
                ("space_translation","momentum"),("rotation","angular_momentum"),
                ("gauge_symmetry","charge_conservation")]),
    PhysicsLaw("Gauge Groups", "group_theory", "",
               ["SU_3","SU_2","U_1"], ["standard_model_gauge_group","strong_force","electroweak"], ConstraintType.DAG_EDGE, None,
               [("SU_3","strong_force"),("SU_2","weak_force"),("U_1","electromagnetism"),
                ("SU_3xSU_2xU_1","standard_model")]),
]



# ===============================================================
# Q: 抽象代数
# ===============================================================

ABSTRACT_ALGEBRA = [
    PhysicsLaw("Ring", "abstract_algebra", "",
               ["group","multiplication"], ["ring","ideal","quotient_ring"], ConstraintType.DAG_EDGE, None,
               [("ring","module"),("ideal","quotient_ring"),("ring","polynomial_ring")]),
    PhysicsLaw("Module", "abstract_algebra", "",
               ["ring"], ["module","free_module","projective_module"], ConstraintType.DAG_EDGE, None,
               [("module","representation"),("free_module","basis"),("projective_module","exact_sequence")]),
    PhysicsLaw("Field Extension", "abstract_algebra", "",
               ["field"], ["field_extension","algebraic_closure","galois_group"], ConstraintType.DAG_EDGE, None,
               [("field_extension","degree"),("galois_group","solvability"),("algebraic_closure","algebraic_geometry")]),
    PhysicsLaw("Galois Theory", "abstract_algebra", "",
               ["field_extension","polynomial_ring"], ["galois_correspondence","radical_extension"], ConstraintType.DAG_EDGE, None,
               [("galois_correspondence","quintic_unsolvability"),("galois_group","symmetric_group")]),
    PhysicsLaw("Algebraic Geometry", "abstract_algebra", "",
               ["commutative_ring","prime_ideal"], ["affine_scheme","coherent_sheaf","cohomology"], ConstraintType.DAG_EDGE, None,
               [("affine_scheme","spectrum"),("algebraic_geometry","string_theory"),("algebraic_geometry","moduli_space")]),
    PhysicsLaw("Clifford Algebra", "abstract_algebra", "",
               ["vector_space","quadratic_form"], ["clifford_algebra","spinor","dirac_operator"], ConstraintType.DAG_EDGE, None,
               [("clifford_algebra","spinor"),("spinor","dirac_equation"),("clifford_algebra","gamma_matrices")]),
    PhysicsLaw("Operator Algebras", "abstract_algebra", "",
               ["vector_space","ring"], ["operator_algebra","c_star_algebra","von_neumann_algebra"], ConstraintType.DAG_EDGE, None,
               [("c_star_algebra","quantum_mechanics"),("operator_algebra","hilbert_space"),("von_neumann_algebra","quantum_field_theory")]),
    PhysicsLaw("Lie Algebra Rep", "abstract_algebra", "",
               ["lie_algebra","representation"], ["root_system","cartan_matrix","dynkin_diagram"], ConstraintType.DAG_EDGE, None,
               [("root_system","weight"),("dynkin_diagram","classification"),("cartan_matrix","kac_moody_algebra")]),
]

# ===============================================================
# R: 范畴论
# ===============================================================

CATEGORY_THEORY = [
    PhysicsLaw("Category", "category_theory", "",
               [], ["category","object","morphism"], ConstraintType.DAG_EDGE, None,
               [("category","functor"),("category","natural_transformation"),("category","universal_property")]),
    PhysicsLaw("Functor", "category_theory", "",
               ["category"], ["functor","covariant_functor","contravariant_functor"], ConstraintType.DAG_EDGE, None,
               [("functor","diagram"),("functor","presheaf"),("contravariant_functor","dual_category")]),
    PhysicsLaw("Natural Transformation", "category_theory", "",
               ["functor"], ["natural_transformation","natural_isomorphism","adjunction"], ConstraintType.DAG_EDGE, None,
               [("natural_transformation","functor_category"),("adjunction","monad"),("adjunction","free_forgetful")]),
    PhysicsLaw("Monad", "category_theory", "",
               ["functor","natural_transformation"], ["monad","kleisli_category","algebra"], ConstraintType.DAG_EDGE, None,
               [("monad","computation"),("monad","algebraic_theory"),("kleisli_category","side_effect")]),
    PhysicsLaw("Chain Complex", "category_theory", "",
               ["module","ring"], ["chain_complex","homology","cohomology"], ConstraintType.DAG_EDGE, None,
               [("chain_complex","boundary_map"),("homology","betti_number"),("cohomology","cup_product"),("chain_complex","derived_category")]),
    PhysicsLaw("Derived Functor", "category_theory", "",
               ["chain_complex","functor"], ["derived_functor","ext_group","tor_group"], ConstraintType.DAG_EDGE, None,
               [("ext_group","extension"),("tor_group","torsion"),("derived_functor","spectral_sequence")]),
    PhysicsLaw("TQFT Categorical", "category_theory", "",
               ["category","cobordism"], ["topological_quantum_field_theory","modular_tensor_category","braided_category"], ConstraintType.DAG_EDGE, None,
               [("modular_tensor_category","anyons"),("braided_category","braid_group"),("topological_quantum_field_theory","jones_polynomial")]),
    PhysicsLaw("BRST Cohomology", "category_theory", "",
               ["gauge_theory","chain_complex"], ["brst_cohomology","ghost_field","gauge_fixing"], ConstraintType.DAG_EDGE, None,
               [("brst_cohomology","physical_state"),("ghost_field","faddeev_popov"),("brst_cohomology","anomaly")]),
    PhysicsLaw("D-brane Category", "category_theory", "",
               ["category","algebraic_geometry"], ["derived_category","d_brane","fukaya_category"], ConstraintType.DAG_EDGE, None,
               [("derived_category","string_theory"),("d_brane","calabi_yau"),("fukaya_category","homological_mirror_symmetry")]),
]


# ===============================================================
# S: 微积分与分析
# ===============================================================

CALCULUS = [
    PhysicsLaw("Derivative", "calculus", "",
               ["function"], ["derivative","tangent_line","rate_of_change"], ConstraintType.DAG_EDGE, None,
               [("derivative","gradient"),("derivative","chain_rule"),("derivative","optimization")]),
    PhysicsLaw("Integral", "calculus", "",
               ["function"], ["integral","antiderivative","area_under_curve"], ConstraintType.DAG_EDGE, None,
               [("integral","fundamental_theorem"),("integral","accumulation")]),
    PhysicsLaw("Fundamental Theorem", "calculus", "",
               ["derivative","integral"], ["fundamental_theorem_of_calculus"], ConstraintType.DAG_EDGE, None,
               [("derivative","integral"),("integral","derivative")]),
    PhysicsLaw("Limit", "calculus", "",
               ["function"], ["limit","continuity","convergence"], ConstraintType.DAG_EDGE, None,
               [("limit","epsilon_delta"),("continuity","intermediate_value"),("convergence","sequence")]),
    PhysicsLaw("Series", "calculus", "",
               ["function"], ["taylor_series","power_series","fourier_series"], ConstraintType.DAG_EDGE, None,
               [("taylor_series","approximation"),("fourier_series","frequency_domain"),
                ("power_series","analytic_function")]),
    PhysicsLaw("Multivariable", "calculus", "",
               ["function","vector_space"], ["partial_derivative","gradient","jacobian","hessian"], ConstraintType.DAG_EDGE, None,
               [("gradient","steepest_descent"),("jacobian","change_of_variables"),
                ("hessian","convexity"),("partial_derivative","directional_derivative")]),
    PhysicsLaw("Vector Calculus", "calculus", "",
               ["vector_field"], ["divergence","curl","laplacian"], ConstraintType.DAG_EDGE, None,
               [("divergence","gauss_theorem"),("curl","stokes_theorem"),
                ("laplacian","poisson_equation"),("gradient","vector_field")]),
    PhysicsLaw("Differential Forms", "calculus", "",
               ["manifold","vector_space"], ["differential_form","exterior_derivative","wedge_product"], ConstraintType.DAG_EDGE, None,
               [("exterior_derivative","stokes_theorem"),("differential_form","de_rham_cohomology"),
                ("wedge_product","volume_form")]),
    PhysicsLaw("ODEs", "calculus", "",
               ["derivative","function"], ["ordinary_differential_equation","initial_value_problem"], ConstraintType.DAG_EDGE, None,
               [("ode","phase_space"),("ode","stability"),("ode","dynamical_system")]),
    PhysicsLaw("PDEs", "calculus", "",
               ["partial_derivative","function"], ["partial_differential_equation","boundary_condition"], ConstraintType.DAG_EDGE, None,
               [("pde","wave_equation"),("pde","heat_equation"),("pde","laplace_equation"),
                ("pde","schrodinger_equation")]),
    PhysicsLaw("Complex Analysis", "calculus", "",
               ["complex_number"], ["holomorphic_function","cauchy_riemann","contour_integral"], ConstraintType.DAG_EDGE, None,
               [("holomorphic_function","analytic"),("contour_integral","residue_theorem"),
                ("cauchy_riemann","harmonic_function")]),
    PhysicsLaw("Functional Analysis", "calculus", "",
               ["vector_space","limit"], ["hilbert_space","banach_space","operator_norm"], ConstraintType.DAG_EDGE, None,
               [("hilbert_space","inner_product"),("banach_space","complete_metric"),
                ("operator_norm","bounded_operator")]),
    # Cross-domain bridges
    PhysicsLaw("Calculus->Physics", "unification", "",
               ["derivative","integral","differential_form"], ["action_principle","lagrangian","euler_lagrange"], ConstraintType.DAG_EDGE, None,
               [("derivative","velocity"),("integral","work"),("differential_form","maxwell_equations"),
                ("gradient","conservative_force"),("laplacian","wave_equation"),
                ("euler_lagrange","least_action"),("taylor_series","perturbation_theory")]),
    PhysicsLaw("Calculus->QM", "unification", "",
               ["derivative","hilbert_space"], ["momentum_operator","schrodinger_equation","path_integral"], ConstraintType.DAG_EDGE, None,
               [("derivative","momentum_operator"),("laplacian","kinetic_energy"),
                ("hilbert_space","quantum_state"),("functional_integral","path_integral")]),
]


# ═══════════════════════════════════════════════════════════════
# C: 粒子物理
# ═══════════════════════════════════════════════════════════════

PARTICLE_PHYSICS = [
    PhysicsLaw("Quark Structure", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("quark","hadron"),("quark","color_charge"),("quark","flavor")]),
    PhysicsLaw("Lepton Family", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("lepton","weak_force"),("lepton","electric_charge"),
                ("lepton","neutrino"),("neutrino","flavor")]),
    PhysicsLaw("Strong Force", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("gluon","color_charge"),("color_charge","strong_force"),
                ("strong_force","confinement"),("strong_force","asymptotic_freedom")]),
    PhysicsLaw("Weak Force", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("weak_force","beta_decay"),("weak_force","neutrino"),
                ("weak_force","flavor"),("weak_force","cp_violation")]),
    PhysicsLaw("Electroweak", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("electroweak","weak_force"),("electroweak","electromagnetic_force"),
                ("electroweak","higgs_field")]),
    PhysicsLaw("Higgs Mechanism", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("higgs_field","higgs_boson"),("higgs_field","mass"),
                ("higgs_boson","mass"),("higgs_mechanism","electroweak")]),
    PhysicsLaw("Confinement", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("confinement","hadron"),("confinement","quark"),
                ("asymptotic_freedom","strong_force")]),
    PhysicsLaw("CP Violation", "particle_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("cp_violation","matter_antimatter_asymmetry"),("cp_violation","flavor")]),
    PhysicsLaw("Particle->Nuclear", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("quark","proton"),("quark","neutron"),("gluon","binding_energy")]),
    PhysicsLaw("Particle->Cosmology", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("higgs_field","inflation"),("quark","big_bang_nucleosynthesis"),
                ("cp_violation","matter_antimatter_asymmetry")]),
]

# ═══════════════════════════════════════════════════════════════
# D: 宇宙学
# ═══════════════════════════════════════════════════════════════

COSMOLOGY = [
    PhysicsLaw("Hubble Law", "cosmology", "",
               ["distance"], ["redshift"], ConstraintType.DAG_EDGE,
               lambda d: d, [("distance","redshift"),("hubble_constant","redshift")]),
    PhysicsLaw("Expansion", "cosmology", "",
               ["density","pressure"], ["expansion_rate"], ConstraintType.DAG_EDGE,
               lambda d,p: d, [("density","expansion_rate"),("pressure","expansion_rate")]),
    PhysicsLaw("Dark Sector", "cosmology", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("dark_energy","expansion_rate"),("dark_matter","structure_formation"),
                ("dark_matter","galaxy_rotation")]),
    PhysicsLaw("Inflation", "cosmology", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("inflation","expansion_rate"),("inflation","structure_formation"),
                ("inflation","cosmic_microwave_background")]),
    PhysicsLaw("CMB", "cosmology", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("cosmic_microwave_background","recombination"),
                ("cosmic_microwave_background","baryon_acoustic_oscillation"),
                ("recombination","redshift")]),
    PhysicsLaw("Structure Formation", "cosmology", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("dark_matter","structure_formation"),("baryon_acoustic_oscillation","structure_formation"),
                ("structure_formation","galaxy_cluster")]),
    PhysicsLaw("BBN", "cosmology", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("big_bang_nucleosynthesis","proton"),("big_bang_nucleosynthesis","neutron"),
                ("big_bang_nucleosynthesis","fusion")]),
]

# ═══════════════════════════════════════════════════════════════
# E: 量子场论
# ═══════════════════════════════════════════════════════════════

QFT = [
    PhysicsLaw("Field Quantization", "quantum_field_theory", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("quantum_field","virtual_particle"),("quantum_field","vacuum_fluctuation")]),
    PhysicsLaw("Path Integral", "quantum_field_theory", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("path_integral","quantum_field"),("path_integral","feynman_diagram"),
                ("action","path_integral")]),
    PhysicsLaw("Feynman Rules", "quantum_field_theory", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("feynman_diagram","s_matrix"),("feynman_diagram","virtual_particle"),
                ("s_matrix","cross_section")]),
    PhysicsLaw("Renormalization", "quantum_field_theory", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("renormalization","coupling_constant"),("renormalization","gauge_theory"),
                ("asymptotic_freedom","renormalization")]),
    PhysicsLaw("Gauge Theory", "quantum_field_theory", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("gauge_theory","quantum_field"),("gauge_theory","strong_force"),
                ("gauge_theory","electroweak"),("gauge_theory","propagator")]),
    PhysicsLaw("Vacuum", "quantum_field_theory", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("vacuum_fluctuation","dark_energy"),("vacuum_fluctuation","virtual_particle"),
                ("vacuum_fluctuation","casimir_effect")]),
    PhysicsLaw("QFT->QM", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("quantum_field","wave_function"),("feynman_diagram","probability"),
                ("s_matrix","measurement")]),
    PhysicsLaw("QFT->GR", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("quantum_field","spacetime_curvature"),("graviton","spacetime_curvature")]),
]

# ═══════════════════════════════════════════════════════════════
# F: 核物理
# ═══════════════════════════════════════════════════════════════

NUCLEAR = [
    PhysicsLaw("Nuclear Binding", "nuclear_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("binding_energy","nuclear_stability"),("proton","binding_energy"),
                ("neutron","binding_energy")]),
    PhysicsLaw("Beta Decay", "nuclear_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("neutron","beta_decay"),("beta_decay","proton"),
                ("beta_decay","neutrino"),("weak_force","beta_decay")]),
    PhysicsLaw("Alpha Decay", "nuclear_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("alpha_decay","half_life"),("alpha_decay","binding_energy"),
                ("alpha_decay","nuclear_decay")]),
    PhysicsLaw("Nuclear Fusion", "nuclear_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("fusion","binding_energy"),("fusion","energy"),
                ("fusion","neutron"),("temperature","fusion")]),
    PhysicsLaw("Nuclear Fission", "nuclear_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("fission","binding_energy"),("fission","energy"),
                ("neutron","fission"),("fission","nuclear_decay")]),
    PhysicsLaw("Decay Chain", "nuclear_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("gamma_decay","photon_energy"),("nuclear_decay","half_life")]),
    PhysicsLaw("Nuclear->Astro", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("fusion","stellar_energy"),("fusion","heavy_elements"),
                ("binding_energy","iron_peak")]),
]

# ═══════════════════════════════════════════════════════════════
# G: 统计力学
# ═══════════════════════════════════════════════════════════════

STATMECH = [
    PhysicsLaw("Ensemble Theory", "statistical_mechanics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("ensemble","partition_function"),("ensemble","ergodicity")]),
    PhysicsLaw("Ergodicity", "statistical_mechanics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("ergodicity","ensemble"),("ergodicity","equilibrium")]),
    PhysicsLaw("Phase Transition", "statistical_mechanics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("phase_transition","critical_point"),("phase_transition","order_parameter"),
                ("critical_point","correlation_function"),("correlation_function","fluctuation")]),
    PhysicsLaw("Fluctuation-Dissipation", "statistical_mechanics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("fluctuation","temperature"),("fluctuation","correlation_function")]),
    PhysicsLaw("Spontaneous Symmetry Breaking", "statistical_mechanics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("spontaneous_symmetry_breaking","phase_transition"),
                ("spontaneous_symmetry_breaking","order_parameter"),
                ("spontaneous_symmetry_breaking","higgs_mechanism")]),
    PhysicsLaw("StatMech->Thermo", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("partition_function","free_energy"),("ensemble","entropy"),
                ("phase_transition","critical_point")]),
]

# ═══════════════════════════════════════════════════════════════
# H: 原子物理
# ═══════════════════════════════════════════════════════════════

ATOMIC = [
    PhysicsLaw("Bohr Model", "atomic_physics", "",
               ["principal_quantum_number"], ["energy_level"], ConstraintType.DAG_EDGE,
               lambda n: -13.6/max(n**2,1), [("principal_quantum_number","energy_level")]),
    PhysicsLaw("Atomic Orbitals", "atomic_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("atomic_orbital","electron_shell"),("atomic_orbital","spectral_line"),
                ("electron_shell","ionization_energy")]),
    PhysicsLaw("Fine Structure", "atomic_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("spin","fine_structure"),("fine_structure","spectral_line"),
                ("fine_structure","hyperfine_structure")]),
    PhysicsLaw("Transition Dipole", "atomic_physics", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("transition_dipole","spectral_line"),("transition_dipole","photon_energy"),
                ("wave_function","transition_dipole")]),
    PhysicsLaw("Atomic->QM", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("hamiltonian","energy_level"),("wave_function","atomic_orbital"),
                ("energy_level","spectral_line")]),
]

# ═══════════════════════════════════════════════════════════════
# I: 人工智能
# ═══════════════════════════════════════════════════════════════

AI = [
    PhysicsLaw("Neural Network", "artificial_intelligence", "",
               ["input_data","weights"], ["output"], ConstraintType.DAG_EDGE,
               lambda x,w: x*w, [("input_data","neural_network"),("weights","neural_network"),
               ("neural_network","output")]),
    PhysicsLaw("Deep Learning", "artificial_intelligence", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("neural_network","deep_learning"),("deep_learning","representation"),
                ("deep_learning","feature_extraction")]),
    PhysicsLaw("LLM Architecture", "artificial_intelligence", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("pretraining","large_language_model"),("large_language_model","fine_tuning"),
                ("fine_tuning","prompting"),("prompting","output")]),
    PhysicsLaw("Emergence", "artificial_intelligence", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("large_language_model","emergence"),("emergence","reasoning"),
                ("emergence","in_context_learning")]),
    PhysicsLaw("AI->Physics", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("neural_network","physics_simulation"),("transformer","symbolic_regression"),
                ("reinforcement_learning","experimental_design")]),
    PhysicsLaw("Physics->AI", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("hamiltonian","neural_network"),("symmetry","equivariant_network"),
                ("entropy","loss_function"),("energy","optimization")]),
]

# ═══════════════════════════════════════════════════════════════
# J: 凝聚态物理
# ═══════════════════════════════════════════════════════════════

CONDENSED_MATTER = [
    PhysicsLaw("Band Theory", "condensed_matter", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("crystal_structure","band_structure"),("band_structure","conductor"),
                ("band_structure","insulator"),("band_structure","semiconductor")]),
    PhysicsLaw("Superconductivity", "condensed_matter", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("cooper_pair","superconductivity"),("electron_phonon","cooper_pair"),
                ("superconductivity","meissner_effect")]),
    PhysicsLaw("Magnetism", "condensed_matter", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("spin","magnetic_order"),("magnetic_order","ferromagnetism"),
                ("magnetic_order","antiferromagnetism")]),
]

# ═══════════════════════════════════════════════════════════════
# K: 量子信息
# ═══════════════════════════════════════════════════════════════

QUANTUM_INFORMATION = [
    PhysicsLaw("Qubit", "quantum_information", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("qubit","superposition"),("qubit","entanglement"),
                ("qubit","quantum_gate")]),
    PhysicsLaw("Quantum Circuit", "quantum_information", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("quantum_gate","quantum_circuit"),("quantum_circuit","quantum_algorithm"),
                ("quantum_circuit","quantum_error_correction")]),
    PhysicsLaw("No Cloning", "quantum_information", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("no_cloning_theorem","quantum_key_distribution"),
                ("no_cloning_theorem","quantum_cryptography")]),
]

# ═══════════════════════════════════════════════════════════════
# L: 微分几何
# ═══════════════════════════════════════════════════════════════

GEOMETRY = [
    PhysicsLaw("Manifold", "geometry", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("manifold","tangent_space"),("manifold","metric_tensor"),
                ("manifold","connection")]),
    PhysicsLaw("Curvature", "geometry", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("connection","curvature"),("curvature","riemann_tensor"),
                ("riemann_tensor","ricci_tensor"),("ricci_tensor","scalar_curvature")]),
    PhysicsLaw("Geometry->GR", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("metric_tensor","spacetime_curvature"),("curvature","einstein_hilbert_action"),
                ("connection","covariant_derivative")]),
]

# ═══════════════════════════════════════════════════════════════
# M: 线性代数
# ═══════════════════════════════════════════════════════════════

LINEAR_ALGEBRA = [
    PhysicsLaw("Linear Space", "linear_algebra", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("vector_space","basis"),("vector_space","dimension"),
                ("linear_transformation","matrix")]),
    PhysicsLaw("Eigen", "linear_algebra", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("matrix","eigenvalue"),("matrix","eigenvector"),
                ("eigenvalue","spectral_decomposition")]),
    PhysicsLaw("Inner Product", "linear_algebra", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("inner_product","orthogonality"),("inner_product","norm"),
                ("inner_product","hilbert_space")]),
    PhysicsLaw("Linear->QM", "unification", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("hilbert_space","wave_function"),("eigenvalue","energy_eigenvalue"),
                ("matrix","operator"),("spectral_decomposition","measurement")]),
]

# ═══════════════════════════════════════════════════════════════
# N: 群论
# ═══════════════════════════════════════════════════════════════

GROUP_THEORY = [
    PhysicsLaw("Group", "group_theory", "",
               [], ["group","identity","inverse","associativity"], ConstraintType.DAG_EDGE, None,
               [("group","subgroup"),("group","homomorphism"),("group","representation")]),
    PhysicsLaw("Lie Group", "group_theory", "",
               ["group","manifold"], ["lie_group","lie_algebra"], ConstraintType.DAG_EDGE, None,
               [("lie_group","generator"),("lie_algebra","structure_constant"),
                ("lie_group","exponential_map")]),
    PhysicsLaw("Representation Theory", "group_theory", "",
               ["group","vector_space"], ["representation","irreducible_representation","character"], ConstraintType.DAG_EDGE, None,
               [("representation","matrix_group"),("irreducible_representation","selection_rule"),
                ("representation","angular_momentum")]),
    PhysicsLaw("Unitary Groups", "group_theory", "",
               ["lie_group","unitary"], ["SU_N","U_1"], ConstraintType.DAG_EDGE, None,
               [("SU_2","spin"),("SU_3","color_charge"),("U_1","electromagnetic_gauge"),
                ("SU_2","weak_isospin")]),
    PhysicsLaw("Lorentz Group", "group_theory", "",
               ["lie_group","spacetime"], ["lorentz_group","poincare_group"], ConstraintType.DAG_EDGE, None,
               [("lorentz_group","spinor"),("poincare_group","mass_casimir"),
                ("lorentz_group","lorentz_transformation")]),
    PhysicsLaw("Noether Theorem", "group_theory", "",
               ["symmetry","lie_group","action"], ["conserved_quantity","noether_charge"], ConstraintType.DAG_EDGE, None,
               [("continuous_symmetry","conserved_current"),("time_translation","energy"),
                ("space_translation","momentum"),("rotation","angular_momentum"),
                ("gauge_symmetry","charge_conservation")]),
    PhysicsLaw("Gauge Groups", "group_theory", "",
               ["SU_3","SU_2","U_1"], ["standard_model_gauge_group","strong_force","electroweak"], ConstraintType.DAG_EDGE, None,
               [("SU_3","strong_force"),("SU_2","weak_force"),("U_1","electromagnetism"),
                ("SU_3xSU_2xU_1","standard_model")]),
]



# ===============================================================
# Q: 抽象代数
# ===============================================================

ABSTRACT_ALGEBRA = [
    PhysicsLaw("Ring", "abstract_algebra", "",
               ["group","multiplication"], ["ring","ideal","quotient_ring"], ConstraintType.DAG_EDGE, None,
               [("ring","module"),("ideal","quotient_ring"),("ring","polynomial_ring")]),
    PhysicsLaw("Module", "abstract_algebra", "",
               ["ring"], ["module","free_module","projective_module"], ConstraintType.DAG_EDGE, None,
               [("module","representation"),("free_module","basis"),("projective_module","exact_sequence")]),
    PhysicsLaw("Field Extension", "abstract_algebra", "",
               ["field"], ["field_extension","algebraic_closure","galois_group"], ConstraintType.DAG_EDGE, None,
               [("field_extension","degree"),("galois_group","solvability"),("algebraic_closure","algebraic_geometry")]),
    PhysicsLaw("Galois Theory", "abstract_algebra", "",
               ["field_extension","polynomial_ring"], ["galois_correspondence","radical_extension"], ConstraintType.DAG_EDGE, None,
               [("galois_correspondence","quintic_unsolvability"),("galois_group","symmetric_group")]),
    PhysicsLaw("Algebraic Geometry", "abstract_algebra", "",
               ["commutative_ring","prime_ideal"], ["affine_scheme","coherent_sheaf","cohomology"], ConstraintType.DAG_EDGE, None,
               [("affine_scheme","spectrum"),("algebraic_geometry","string_theory"),("algebraic_geometry","moduli_space")]),
    PhysicsLaw("Clifford Algebra", "abstract_algebra", "",
               ["vector_space","quadratic_form"], ["clifford_algebra","spinor","dirac_operator"], ConstraintType.DAG_EDGE, None,
               [("clifford_algebra","spinor"),("spinor","dirac_equation"),("clifford_algebra","gamma_matrices")]),
    PhysicsLaw("Operator Algebras", "abstract_algebra", "",
               ["vector_space","ring"], ["operator_algebra","c_star_algebra","von_neumann_algebra"], ConstraintType.DAG_EDGE, None,
               [("c_star_algebra","quantum_mechanics"),("operator_algebra","hilbert_space"),("von_neumann_algebra","quantum_field_theory")]),
    PhysicsLaw("Lie Algebra Rep", "abstract_algebra", "",
               ["lie_algebra","representation"], ["root_system","cartan_matrix","dynkin_diagram"], ConstraintType.DAG_EDGE, None,
               [("root_system","weight"),("dynkin_diagram","classification"),("cartan_matrix","kac_moody_algebra")]),
]

# ===============================================================
# R: 范畴论
# ===============================================================

CATEGORY_THEORY = [
    PhysicsLaw("Category", "category_theory", "",
               [], ["category","object","morphism"], ConstraintType.DAG_EDGE, None,
               [("category","functor"),("category","natural_transformation"),("category","universal_property")]),
    PhysicsLaw("Functor", "category_theory", "",
               ["category"], ["functor","covariant_functor","contravariant_functor"], ConstraintType.DAG_EDGE, None,
               [("functor","diagram"),("functor","presheaf"),("contravariant_functor","dual_category")]),
    PhysicsLaw("Natural Transformation", "category_theory", "",
               ["functor"], ["natural_transformation","natural_isomorphism","adjunction"], ConstraintType.DAG_EDGE, None,
               [("natural_transformation","functor_category"),("adjunction","monad"),("adjunction","free_forgetful")]),
    PhysicsLaw("Monad", "category_theory", "",
               ["functor","natural_transformation"], ["monad","kleisli_category","algebra"], ConstraintType.DAG_EDGE, None,
               [("monad","computation"),("monad","algebraic_theory"),("kleisli_category","side_effect")]),
    PhysicsLaw("Chain Complex", "category_theory", "",
               ["module","ring"], ["chain_complex","homology","cohomology"], ConstraintType.DAG_EDGE, None,
               [("chain_complex","boundary_map"),("homology","betti_number"),("cohomology","cup_product"),("chain_complex","derived_category")]),
    PhysicsLaw("Derived Functor", "category_theory", "",
               ["chain_complex","functor"], ["derived_functor","ext_group","tor_group"], ConstraintType.DAG_EDGE, None,
               [("ext_group","extension"),("tor_group","torsion"),("derived_functor","spectral_sequence")]),
    PhysicsLaw("TQFT Categorical", "category_theory", "",
               ["category","cobordism"], ["topological_quantum_field_theory","modular_tensor_category","braided_category"], ConstraintType.DAG_EDGE, None,
               [("modular_tensor_category","anyons"),("braided_category","braid_group"),("topological_quantum_field_theory","jones_polynomial")]),
    PhysicsLaw("BRST Cohomology", "category_theory", "",
               ["gauge_theory","chain_complex"], ["brst_cohomology","ghost_field","gauge_fixing"], ConstraintType.DAG_EDGE, None,
               [("brst_cohomology","physical_state"),("ghost_field","faddeev_popov"),("brst_cohomology","anomaly")]),
    PhysicsLaw("D-brane Category", "category_theory", "",
               ["category","algebraic_geometry"], ["derived_category","d_brane","fukaya_category"], ConstraintType.DAG_EDGE, None,
               [("derived_category","string_theory"),("d_brane","calabi_yau"),("fukaya_category","homological_mirror_symmetry")]),
]


# ===============================================================
# T: 图论 — 脑在走图，应认识图
# ===============================================================

GRAPH_THEORY = [
    PhysicsLaw("Graph", "graph_theory", "",
               [], ["graph","vertex","edge"], ConstraintType.DAG_EDGE, None,
               [("graph","directed_graph"),("graph","undirected_graph"),("vertex","neighbor"),
                ("edge","path"),("graph","adjacency_matrix")]),
    PhysicsLaw("Connectivity", "graph_theory", "",
               ["graph"], ["connected_component","reachability","strongly_connected"], ConstraintType.DAG_EDGE, None,
               [("connected_component","bridge"),("reachability","transitive_closure"),
                ("strongly_connected","cycle")]),
    PhysicsLaw("Centrality", "graph_theory", "",
               ["graph","vertex"], ["degree_centrality","betweenness_centrality","pagerank"], ConstraintType.DAG_EDGE, None,
               [("degree_centrality","hub"),("betweenness_centrality","bottleneck"),
                ("pagerank","importance")]),
    PhysicsLaw("Shortest Path", "graph_theory", "",
               ["graph","edge"], ["shortest_path","dijkstra","bellman_ford"], ConstraintType.DAG_EDGE, None,
               [("shortest_path","distance"),("dijkstra","weighted_graph"),
                ("bellman_ford","negative_cycle")]),
    PhysicsLaw("Spanning Tree", "graph_theory", "",
               ["graph","edge"], ["spanning_tree","minimum_spanning_tree","forest"], ConstraintType.DAG_EDGE, None,
               [("spanning_tree","cycle_free"),("minimum_spanning_tree","kruskal"),
                ("forest","disconnected")]),
    PhysicsLaw("DAG", "graph_theory", "",
               ["graph","edge"], ["directed_acyclic_graph","topological_sort","dag"], ConstraintType.DAG_EDGE, None,
               [("dag","causal_graph"),("topological_sort","partial_order"),
                ("dag","bayesian_network")]),
    PhysicsLaw("Network Flow", "graph_theory", "",
               ["graph","edge"], ["network_flow","max_flow_min_cut","ford_fulkerson"], ConstraintType.DAG_EDGE, None,
               [("network_flow","capacity"),("max_flow_min_cut","bottleneck"),
                ("ford_fulkerson","augmenting_path")]),
    # 跨域桥: 图论→物理
    PhysicsLaw("Graph->Causal", "unification", "",
               ["dag","causal_graph"], ["causal_discovery","intervention_calculus"], ConstraintType.DAG_EDGE, None,
               [("dag","causal_graph"),("causal_discovery","do_calculus"),
                ("directed_graph","causal_direction"),("reachability","causal_effect")]),
    PhysicsLaw("Graph->Network", "unification", "",
               ["graph","network_flow"], ["neural_network_graph","knowledge_graph"], ConstraintType.DAG_EDGE, None,
               [("graph","knowledge_graph"),("centrality","attention"),
                ("shortest_path","inference_chain"),("graph","semantic_network")]),
]

# ===============================================================
# U: 流体力学
# ===============================================================

FLUIDS = [
    PhysicsLaw("Continuity Eq", "fluids", "",
               ["density","velocity"], ["mass_flux"], ConstraintType.DAG_EDGE, None,
               [("density","mass_conservation"),("velocity","mass_flux"),
                ("divergence","continuity_equation")]),
    PhysicsLaw("Navier-Stokes", "fluids", "",
               ["velocity","pressure","viscosity"], ["fluid_acceleration"], ConstraintType.DAG_EDGE, None,
               [("pressure_gradient","fluid_acceleration"),("viscosity","dissipation"),
                ("velocity","convection"),("navier_stokes","turbulence")]),
    PhysicsLaw("Bernoulli", "fluids", "",
               ["velocity","pressure","density"], ["bernoulli_constant"], ConstraintType.DAG_EDGE, None,
               [("velocity","dynamic_pressure"),("pressure","static_pressure"),
                ("bernoulli_principle","energy_conservation")]),
    PhysicsLaw("Reynolds Number", "fluids", "",
               ["velocity","viscosity","length_scale"], ["reynolds_number","flow_regime"], ConstraintType.DAG_EDGE, None,
               [("reynolds_number","laminar_flow"),("reynolds_number","turbulent_flow"),
                ("reynolds_number","transition_to_turbulence")]),
    PhysicsLaw("Turbulence", "fluids", "",
               ["navier_stokes","reynolds_number"], ["turbulence","energy_cascade","kolmogorov_scale"], ConstraintType.DAG_EDGE, None,
               [("turbulence","eddy"),("energy_cascade","kolmogorov_spectrum"),
                ("turbulence","mixing"),("turbulence","drag")]),
    PhysicsLaw("Boundary Layer", "fluids", "",
               ["viscosity","velocity"], ["boundary_layer","shear_stress","flow_separation"], ConstraintType.DAG_EDGE, None,
               [("boundary_layer","no_slip"),("shear_stress","skin_friction"),
                ("flow_separation","pressure_drag")]),
    PhysicsLaw("Vorticity", "fluids", "",
               ["velocity","curl"], ["vorticity","circulation","vortex"], ConstraintType.DAG_EDGE, None,
               [("vorticity","helmholtz_theorem"),("circulation","lift"),
                ("vortex","vortex_shedding")]),
    PhysicsLaw("Compressible Flow", "fluids", "",
               ["density","pressure","velocity"], ["mach_number","shock_wave","expansion_fan"], ConstraintType.DAG_EDGE, None,
               [("mach_number","supersonic"),("shock_wave","discontinuity"),
                ("expansion_fan","isentropic")]),
    # 跨域桥
    PhysicsLaw("Fluids->Astro", "unification", "",
               ["turbulence","magnetic_field"], ["magnetohydrodynamics","accretion_disk","stellar_convection"], ConstraintType.DAG_EDGE, None,
               [("magnetohydrodynamics","plasma"),("turbulence","interstellar_medium"),
                ("accretion_disk","angular_momentum_transport")]),
    PhysicsLaw("Fluids->QFT", "unification", "",
               ["navier_stokes","quantum_field"], ["quantum_hydrodynamics","superfluid"], ConstraintType.DAG_EDGE, None,
               [("quantum_hydrodynamics","bose_einstein_condensate"),("superfluid","zero_viscosity"),
                ("vorticity","quantized_vortex")]),
]

# ===============================================================
# I+: 人工智能扩展 (恢复完整版)
# ===============================================================

AI_EXTENDED = [
    PhysicsLaw("Backpropagation", "artificial_intelligence", "",
               ["loss_function","output"], ["gradient"], ConstraintType.DAG_EDGE,
               lambda l,o: l*o, [("loss_function","gradient"),("output","gradient"),
               ("gradient","weights")]),
    PhysicsLaw("Gradient Descent", "artificial_intelligence", "",
               ["gradient","learning_rate"], ["weights"], ConstraintType.DAG_EDGE,
               lambda g,lr: g*lr, [("gradient","weights"),("learning_rate","weights")]),
    PhysicsLaw("Transformer", "artificial_intelligence", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("attention","transformer"),("transformer","embedding"),
                ("transformer","sequence_modeling"),("transformer","large_language_model")]),
    PhysicsLaw("Training Dynamics", "artificial_intelligence", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("training_data","neural_network"),("training_data","overfitting"),
                ("regularization","overfitting"),("overfitting","generalization")]),
    PhysicsLaw("Reinforcement Learning", "artificial_intelligence", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("reward_function","policy_gradient"),("policy_gradient","reinforcement_learning"),
                ("reinforcement_learning","exploration"),("reinforcement_learning","exploitation")]),
    PhysicsLaw("Generative Models", "artificial_intelligence", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("generative_model","diffusion"),("generative_model","autoencoder"),
                ("diffusion","image_generation"),("autoencoder","representation")]),
    PhysicsLaw("Scaling Laws", "artificial_intelligence", "",
               [], [], ConstraintType.DAG_EDGE, None,
               [("model_size","performance"),("training_data","performance"),
                ("compute_budget","performance")]),
]


# ===============================================================
# V: 天体物理
# ===============================================================

ASTROPHYSICS = [
    PhysicsLaw("Stellar Structure", "astrophysics", "",
               ["mass","gravity","pressure"], ["stellar_equilibrium","hydrostatic_balance"], ConstraintType.DAG_EDGE, None,
               [("gravity","stellar_collapse"),("pressure","stellar_support"),
                ("mass","stellar_evolution"),("temperature","nuclear_burning")]),
    PhysicsLaw("Stellar Evolution", "astrophysics", "",
               ["mass","stellar_equilibrium"], ["main_sequence","red_giant","white_dwarf","supernova"], ConstraintType.DAG_EDGE, None,
               [("main_sequence","hydrogen_burning"),("red_giant","helium_flash"),
                ("white_dwarf","electron_degeneracy"),("supernova","neutron_star")]),
    PhysicsLaw("Compact Objects", "astrophysics", "",
               ["gravity","density"], ["neutron_star","black_hole","event_horizon"], ConstraintType.DAG_EDGE, None,
               [("neutron_star","pulsar"),("black_hole","accretion_disk"),
                ("event_horizon","hawking_radiation"),("black_hole","gravitational_wave")]),
    PhysicsLaw("Galaxy Formation", "astrophysics", "",
               ["dark_matter","gas"], ["galaxy","spiral_galaxy","elliptical_galaxy"], ConstraintType.DAG_EDGE, None,
               [("dark_matter","galaxy_rotation_curve"),("gas","star_formation"),
                ("galaxy","supermassive_black_hole")]),
    PhysicsLaw("Interstellar Medium", "astrophysics", "",
               ["gas","dust","radiation"], ["ism","molecular_cloud","hii_region"], ConstraintType.DAG_EDGE, None,
               [("molecular_cloud","star_formation"),("hii_region","ionization"),
                ("ism","extinction"),("cosmic_rays","ism")]),
    PhysicsLaw("Exoplanets", "astrophysics", "",
               ["planet","star"], ["exoplanet","habitable_zone","transit_method"], ConstraintType.DAG_EDGE, None,
               [("transit_method","light_curve"),("habitable_zone","liquid_water"),
                ("exoplanet","atmosphere")]),
    PhysicsLaw("High Energy Astro", "astrophysics", "",
               ["magnetic_field","gravity"], ["active_galactic_nucleus","quasar","gamma_ray_burst"], ConstraintType.DAG_EDGE, None,
               [("agn","relativistic_jet"),("quasar","supermassive_black_hole"),
                ("gamma_ray_burst","afterglow")]),
]

# ===============================================================
# W: 等离子体物理
# ===============================================================

PLASMA = [
    PhysicsLaw("Plasma State", "plasma_physics", "",
               ["temperature","density"], ["plasma","debye_length","plasma_frequency"], ConstraintType.DAG_EDGE, None,
               [("plasma","quasineutrality"),("debye_length","screening"),
                ("plasma_frequency","langmuir_wave")]),
    PhysicsLaw("MHD", "plasma_physics", "",
               ["magnetic_field","plasma"], ["magnetohydrodynamics","alfven_wave","magnetic_reconnection"], ConstraintType.DAG_EDGE, None,
               [("alfven_wave","magnetic_tension"),("magnetic_reconnection","solar_flare"),
                ("mhd","fusion_plasma")]),
    PhysicsLaw("Plasma Instabilities", "plasma_physics", "",
               ["plasma","magnetic_field"], ["kink_instability","sausage_instability","two_stream_instability"], ConstraintType.DAG_EDGE, None,
               [("kink_instability","tokamak"),("two_stream_instability","beam_plasma"),
                ("instability","turbulence")]),
    PhysicsLaw("Fusion", "plasma_physics", "",
               ["plasma","temperature","density"], ["fusion","lawson_criterion","tokamak"], ConstraintType.DAG_EDGE, None,
               [("fusion","d_t_reaction"),("lawson_criterion","ignition"),
                ("tokamak","magnetic_confinement"),("fusion","stellarator")]),
    PhysicsLaw("Space Plasma", "plasma_physics", "",
               ["solar_wind","magnetic_field"], ["magnetosphere","aurora","bow_shock"], ConstraintType.DAG_EDGE, None,
               [("solar_wind","magnetosphere"),("magnetosphere","van_allen_belt"),
                ("aurora","particle_precipitation")]),
]

# ===============================================================
# X: 声学
# ===============================================================

ACOUSTICS = [
    PhysicsLaw("Sound Waves", "acoustics", "",
               ["pressure","density"], ["sound_wave","longitudinal_wave","speed_of_sound"], ConstraintType.DAG_EDGE, None,
               [("pressure","compression"),("density","sound_speed"),
                ("sound_wave","wavelength"),("sound_wave","frequency")]),
    PhysicsLaw("Wave Equation", "acoustics", "",
               ["pressure","time"], ["wave_equation","d Alembert_solution","standing_wave"], ConstraintType.DAG_EDGE, None,
               [("wave_equation","propagation"),("standing_wave","resonance"),
                ("standing_wave","harmonics")]),
    PhysicsLaw("Impedance", "acoustics", "",
               ["density","sound_speed"], ["acoustic_impedance","reflection_coefficient","transmission_coefficient"], ConstraintType.DAG_EDGE, None,
               [("acoustic_impedance","mismatch"),("reflection_coefficient","echo"),
                ("transmission_coefficient","refraction")]),
    PhysicsLaw("Doppler Effect", "acoustics", "",
               ["velocity","frequency"], ["doppler_shift","redshift","blueshift"], ConstraintType.DAG_EDGE, None,
               [("doppler_shift","relative_velocity"),("redshift","receding_source"),
                ("blueshift","approaching_source")]),
    PhysicsLaw("Nonlinear Acoustics", "acoustics", "",
               ["pressure","amplitude"], ["shock_wave_acoustic","soliton","parametric_array"], ConstraintType.DAG_EDGE, None,
               [("shock_wave_acoustic","nonlinear_steepening"),("soliton","dispersion"),
                ("parametric_array","frequency_conversion")]),
]

# ===============================================================
# Y: 数值方法
# ===============================================================

NUMERICAL = [
    PhysicsLaw("Monte Carlo", "numerical_methods", "",
               ["probability_distribution","random_sampling"], ["monte_carlo","importance_sampling","markov_chain_monte_carlo"], ConstraintType.DAG_EDGE, None,
               [("monte_carlo","uncertainty_quantification"),("mcmc","bayesian_inference"),
                ("importance_sampling","variance_reduction")]),
    PhysicsLaw("Finite Elements", "numerical_methods", "",
               ["pde","mesh"], ["finite_element_method","basis_function","stiffness_matrix"], ConstraintType.DAG_EDGE, None,
               [("fem","structural_analysis"),("fem","electromagnetics"),
                ("fem","heat_transfer")]),
    PhysicsLaw("Finite Difference", "numerical_methods", "",
               ["derivative","grid"], ["finite_difference","cfl_condition","numerical_stability"], ConstraintType.DAG_EDGE, None,
               [("finite_difference","time_stepping"),("cfl_condition","convergence"),
                ("numerical_stability","dissipation")]),
    PhysicsLaw("Optimization", "numerical_methods", "",
               ["function","gradient"], ["optimization","gradient_descent","newton_method","simulated_annealing"], ConstraintType.DAG_EDGE, None,
               [("gradient_descent","local_minimum"),("newton_method","hessian"),
                ("simulated_annealing","global_optimum")]),
    PhysicsLaw("Linear Algebra Num", "numerical_methods", "",
               ["matrix","vector"], ["svd","qr_decomposition","conjugate_gradient","eigenvalue_solver"], ConstraintType.DAG_EDGE, None,
               [("svd","low_rank_approximation"),("qr_decomposition","least_squares"),
                ("conjugate_gradient","sparse_system")]),
    PhysicsLaw("FFT", "numerical_methods", "",
               ["signal","frequency"], ["fourier_transform","fft","spectral_method"], ConstraintType.DAG_EDGE, None,
               [("fft","frequency_domain"),("spectral_method","pde_solver"),
                ("fourier_transform","convolution")]),
]

# ===============================================================
# Z: 混沌与非线性动力学
# ===============================================================

CHAOS = [
    PhysicsLaw("Nonlinear Dynamics", "chaos_theory", "",
               ["ode","nonlinear"], ["fixed_point","limit_cycle","strange_attractor"], ConstraintType.DAG_EDGE, None,
               [("fixed_point","stability"),("limit_cycle","oscillation"),
                ("strange_attractor","chaos")]),
    PhysicsLaw("Lyapunov", "chaos_theory", "",
               ["trajectory","perturbation"], ["lyapunov_exponent","sensitive_dependence","predictability_horizon"], ConstraintType.DAG_EDGE, None,
               [("lyapunov_exponent","chaos"),("sensitive_dependence","butterfly_effect"),
                ("predictability_horizon","deterministic")]),
    PhysicsLaw("Bifurcation", "chaos_theory", "",
               ["parameter","fixed_point"], ["bifurcation","period_doubling","feigenbaum_constant"], ConstraintType.DAG_EDGE, None,
               [("bifurcation","qualitative_change"),("period_doubling","route_to_chaos"),
                ("feigenbaum_constant","universality")]),
    PhysicsLaw("Fractals", "chaos_theory", "",
               ["self_similarity","scale"], ["fractal","fractal_dimension","mandelbrot_set"], ConstraintType.DAG_EDGE, None,
               [("fractal","self_similarity"),("fractal_dimension","hausdorff"),
                ("mandelbrot_set","complex_dynamics")]),
    # 跨域桥
    PhysicsLaw("Chaos->Physics", "unification", "",
               ["lyapunov_exponent","bifurcation"], ["quantum_chaos","turbulence","double_pendulum"], ConstraintType.DAG_EDGE, None,
               [("quantum_chaos","random_matrix"),("turbulence","energy_cascade"),
                ("double_pendulum","classical_chaos"),("chaos","ergodicity")]),
]

TOPOLOGY = [
    # ── 拓扑基础 ──
    PhysicsLaw("Topological Space", "topology", "",
               [], ["topological_space","open_set","continuity"], ConstraintType.DAG_EDGE, None,
               [("topological_space","homotopy"),("topological_space","homology")]),
    PhysicsLaw("Homotopy", "topology", "",
               ["topological_space"], ["homotopy_group","fundamental_group"], ConstraintType.DAG_EDGE, None,
               [("fundamental_group","winding_number"),("homotopy_group","topological_invariant")]),
    PhysicsLaw("Homology", "topology", "",
               ["topological_space"], ["homology_group","betti_number","euler_characteristic"], ConstraintType.DAG_EDGE, None,
               [("betti_number","genus"),("homology_group","cohomology")]),
    
    # ── 纤维丛 ──
    PhysicsLaw("Fiber Bundle", "topology", "",
               ["topological_space","group"], ["fiber_bundle","principal_bundle","associated_bundle"], ConstraintType.DAG_EDGE, None,
               [("fiber_bundle","section"),("principal_bundle","connection"),
                ("associated_bundle","matter_field")]),
    PhysicsLaw("Characteristic Classes", "topology", "",
               ["fiber_bundle"], ["chern_class","pontryagin_class","euler_class"], ConstraintType.DAG_EDGE, None,
               [("chern_class","chern_simons"),("chern_class","topological_invariant"),
                ("chern_simons","topological_field_theory")]),
    
    # ── 跨域桥: 拓扑→凝聚态 ──
    PhysicsLaw("Topological Matter", "topology", "",
               ["topological_invariant","chern_class"], ["topological_insulator","quantum_hall_effect","topological_order"], ConstraintType.DAG_EDGE, None,
               [("chern_number","quantum_hall_effect"),("topological_invariant","topological_insulator"),
                ("topological_order","anyons")]),
    
    # ── 跨域桥: 拓扑→量子场论 ──
    PhysicsLaw("Topological QFT", "topology", "",
               ["chern_simons","topological_invariant"], ["topological_field_theory","anyon_statistics"], ConstraintType.DAG_EDGE, None,
               [("chern_simons","topological_field_theory"),("braid_group","anyon_statistics"),
                ("topological_field_theory","quantum_computation")]),
]

PROBABILITY_THEORY = [
    # ── 概率基础 ──
    PhysicsLaw("Probability Space", "probability_theory", "",
               [], ["probability_space","random_variable","expectation"], ConstraintType.DAG_EDGE, None,
               [("probability_space","probability_distribution"),("random_variable","moment")]),
    PhysicsLaw("Bayes Theorem", "probability_theory", "",
               ["probability_space"], ["bayes_theorem","prior","posterior","likelihood"], ConstraintType.DAG_EDGE, None,
               [("bayes_theorem","inference"),("likelihood","maximum_likelihood")]),
    
    # ── 信息论 ──
    PhysicsLaw("Shannon Entropy", "probability_theory", "",
               ["probability_distribution"], ["shannon_entropy","information","mutual_information"], ConstraintType.DAG_EDGE, None,
               [("shannon_entropy","uncertainty"),("mutual_information","correlation")]),
    PhysicsLaw("KL Divergence", "probability_theory", "",
               ["probability_distribution"], ["kl_divergence","relative_entropy"], ConstraintType.DAG_EDGE, None,
               [("kl_divergence","free_energy"),("relative_entropy","model_selection")]),
    
    # ── 随机过程 ──
    PhysicsLaw("Stochastic Process", "probability_theory", "",
               ["probability_space","time"], ["stochastic_process","markov_chain","brownian_motion"], ConstraintType.DAG_EDGE, None,
               [("stochastic_process","correlation_function"),("markov_chain","transition_matrix"),
                ("brownian_motion","diffusion")]),
    
    # ── 跨域桥: 概率→统计力学 ──
    PhysicsLaw("Statistical Ensembles", "probability_theory", "",
               ["probability_distribution","shannon_entropy"], ["partition_function","ensemble","boltzmann_distribution"], ConstraintType.DAG_EDGE, None,
               [("shannon_entropy","statistical_entropy"),("partition_function","free_energy"),
                ("probability_distribution","boltzmann_distribution")]),
    
    # ── 跨域桥: 概率→量子力学 ──
    PhysicsLaw("Born Rule", "probability_theory", "",
               ["probability_space","inner_product"], ["born_rule","probability_amplitude","measurement_outcome"], ConstraintType.DAG_EDGE, None,
               [("probability_amplitude","wave_function"),("born_rule","quantum_measurement"),
                ("probability_distribution","measurement_statistics")]),
    
    # ── 跨域桥: 概率→信息物理 ──
    PhysicsLaw("Information Physics", "probability_theory", "",
               ["shannon_entropy","thermodynamics"], ["landauer_principle","maxwell_demon","information_entropy"], ConstraintType.DAG_EDGE, None,
               [("shannon_entropy","thermodynamic_entropy"),("information","work"),
                ("landauer_principle","energy_cost_of_computation")]),
]
ALL_ENRICHMENT = (FORMULA_AND_TEMPLATES + PARTICLE_PHYSICS + COSMOLOGY + 
                  QFT + NUCLEAR + STATMECH + ATOMIC + AI + 
                  CONDENSED_MATTER + QUANTUM_INFORMATION + GEOMETRY + LINEAR_ALGEBRA +
                  GROUP_THEORY + TOPOLOGY + PROBABILITY_THEORY +
                  ABSTRACT_ALGEBRA + CATEGORY_THEORY +
                  CALCULUS + GRAPH_THEORY + FLUIDS + AI_EXTENDED +
                  ASTROPHYSICS + PLASMA + ACOUSTICS + NUMERICAL + CHAOS)

_ENRICHED = False


def feed_enrichment(force: bool = False) -> int:
    """注入所有加料到 library。幂等: 重复调用不会重复添加。
    
    持久化: 注册到 library._laws，colony 启动时自动加载。
    """
    global _ENRICHED
    if _ENRICHED and not force:
        return 0
    
    existing_edges = set()
    for law in library._laws:
        for src, dst in law.causal_direction:
            existing_edges.add((src, dst))
    
    added = 0
    new_edges = 0
    
    for law in ALL_ENRICHMENT:
        new_for_this_law = []
        for src, dst in law.causal_direction:
            if (src, dst) not in existing_edges:
                new_for_this_law.append((src, dst))
                existing_edges.add((src, dst))
        
        if new_for_this_law:
            library._laws.append(law)
            added += 1
            new_edges += len(new_for_this_law)
    
    _ENRICHED = True
    if added > 0:
        print(f"🧪 物理加料: +{added}定律, +{new_edges}边 "
              f"({sum(len(l.causal_direction) for l in library._laws)}总边)")
    return added


# ═══════════════════════════════════════════════════════════════


def _auto_enrich():
    try:
        feed_enrichment()
    except Exception:
        pass


if __name__ == "__main__":
    feed_enrichment()
    nodes = set()
    edges = 0
    domains = {}
    for law in library._laws:
        d = law.domain
        domains[d] = domains.get(d, 0) + 1
        for src, dst in law.causal_direction:
            nodes.add(src)
            nodes.add(dst)
            edges += 1
    print(f"   {len(nodes)}概念 {edges}边 {len(domains)}域")
    print(f"   密度: 6000神经元/{edges}边 = {6000/edges:.1f} 神经元/边")
