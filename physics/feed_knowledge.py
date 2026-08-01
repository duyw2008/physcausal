"""
知识喂养 — 桥接稀疏域, 扩图到 500+ 边
"""
from physics.laws import PhysicsLaw, ConstraintType, library


def feed_knowledge():
    """批量注册跨域桥接定律。"""
    bridges = [
        # ═══ condensed_matter ↔ quantum/optics ═══
        PhysicsLaw(
            name="BlochTheorem", domain="condensed_matter",
            latex=r"periodic_potential → band_structure",
            inputs=["periodic_potential"], outputs=["band_structure"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda periodic_potential: 1.0,
            causal_direction=[("periodic_potential", "band_structure")],
        ),
        PhysicsLaw(
            name="BandGapToOpticalGap", domain="condensed_matter",
            latex=r"E_g = hc/λ",
            inputs=["band_structure"], outputs=["optical_gap"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda band_structure: 1.0,
            causal_direction=[("band_structure", "optical_gap")],
        ),
        PhysicsLaw(
            name="FermiSurfaceConductivity", domain="condensed_matter",
            latex=r"band_structure → conductivity",
            inputs=["band_structure"], outputs=["electrical_conductivity"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda band_structure: 1.0,
            causal_direction=[("band_structure", "electrical_conductivity")],
        ),
        PhysicsLaw(
            name="PhononThermalConductivity", domain="condensed_matter",
            latex=r"phonon_dispersion → thermal_conductivity",
            inputs=["phonon_dispersion"], outputs=["thermal_conductivity"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda phonon_dispersion: 1.0,
            causal_direction=[("phonon_dispersion", "thermal_conductivity")],
        ),
        # CM → thermo bridge
        PhysicsLaw(
            name="ThermalConductivityToTemperature", domain="thermodynamics",
            latex=r"∇·(κ∇T) → T distribution",
            inputs=["thermal_conductivity"], outputs=["temperature"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda thermal_conductivity: 1.0,
            causal_direction=[("thermal_conductivity", "temperature")],
        ),
        
        # ═══ fluids ↔ thermo ═══
        PhysicsLaw(
            name="PressureTemperatureIdealGas", domain="thermodynamics",
            latex=r"P = nRT/V",
            inputs=["pressure"], outputs=["temperature"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda pressure: 1.0,
            causal_direction=[("pressure", "temperature")],
        ),
        PhysicsLaw(
            name="ViscousEntropy", domain="thermodynamics",
            latex=r"viscosity → entropy",
            inputs=["fluid_viscosity"], outputs=["entropy"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda fluid_viscosity: 1.0,
            causal_direction=[("fluid_viscosity", "entropy")],
        ),
        # fluids → acoustics
        PhysicsLaw(
            name="PressureToSoundSpeed", domain="acoustics",
            latex=r"c = √(γP/ρ)",
            inputs=["pressure"], outputs=["sound_speed"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda pressure: 1.0,
            causal_direction=[("pressure", "sound_speed")],
        ),
        
        # ═══ relativity ↔ quantum ═══
        PhysicsLaw(
            name="ComptonWavelength", domain="quantum",
            latex=r"λ_C = h/mc",
            inputs=["mass"], outputs=["compton_wavelength"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda mass: 1.0,
            causal_direction=[("mass", "compton_wavelength")],
        ),
        PhysicsLaw(
            name="ComptonToEnergy", domain="quantum",
            latex=r"λ_C → photon_energy",
            inputs=["compton_wavelength"], outputs=["photon_energy"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda compton_wavelength: 1.0,
            causal_direction=[("compton_wavelength", "photon_energy")],
        ),
        PhysicsLaw(
            name="RelativisticEnergyMomentum", domain="relativity",
            latex=r"E² = (pc)² + (mc²)²",
            inputs=["momentum", "mass"], outputs=["energy"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda momentum, mass: 1.0,
            causal_direction=[("momentum", "energy"), ("mass", "energy")],
        ),
        
        # ═══ quantum ↔ thermo ═══
        PhysicsLaw(
            name="UnruhEffect", domain="quantum",
            latex=r"T = ħa/2πkc",
            inputs=["acceleration"], outputs=["unruh_temperature"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda acceleration: 1.0,
            causal_direction=[("acceleration", "unruh_temperature")],
        ),
        PhysicsLaw(
            name="UnruhToTemperature", domain="thermodynamics",
            latex=r"T_Unruh → temperature",
            inputs=["unruh_temperature"], outputs=["temperature"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda unruh_temperature: 1.0,
            causal_direction=[("unruh_temperature", "temperature")],
        ),
        # quantum → mechanics
        PhysicsLaw(
            name="CasimirForce", domain="quantum",
            latex=r"vacuum → Casimir force",
            inputs=["vacuum_fluctuation"], outputs=["casimir_force"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda vacuum_fluctuation: 1.0,
            causal_direction=[("vacuum_fluctuation", "casimir_force")],
        ),
        PhysicsLaw(
            name="CasimirToMechanics", domain="mechanics",
            latex=r"F_Casimir → force",
            inputs=["casimir_force"], outputs=["force"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda casimir_force: 1.0,
            causal_direction=[("casimir_force", "force")],
        ),
        
        # ═══ GR ↔ classical ═══
        PhysicsLaw(
            name="NewtonianLimit", domain="general_relativity",
            latex=r"g_00 ≈ -(1+2Φ/c²)",
            inputs=["spacetime_curvature"], outputs=["gravitational_potential"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda spacetime_curvature: 1.0,
            causal_direction=[("spacetime_curvature", "gravitational_potential")],
        ),
        PhysicsLaw(
            name="PotentialToForceGravity", domain="mechanics",
            latex=r"F = -m∇Φ",
            inputs=["gravitational_potential"], outputs=["force_gravity"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda gravitational_potential: 1.0,
            causal_direction=[("gravitational_potential", "force_gravity")],
        ),
        
        # ═══ acoustics ↔ mechanics/thermo ═══
        PhysicsLaw(
            name="SoundPressureForce", domain="mechanics",
            latex=r"sound_pressure → force",
            inputs=["sound_pressure"], outputs=["force"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda sound_pressure: 1.0,
            causal_direction=[("sound_pressure", "force")],
        ),
        PhysicsLaw(
            name="AcousticHeating", domain="thermodynamics",
            latex=r"acoustic_energy → T",
            inputs=["acoustic_energy"], outputs=["temperature"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda acoustic_energy: 1.0,
            causal_direction=[("acoustic_energy", "temperature")],
        ),
        
        # ═══ EM ↔ optics ↔ CM ═══
        PhysicsLaw(
            name="MagneticMomentForce", domain="electromagnetism",
            latex=r"μ → force",
            inputs=["magnetic_moment"], outputs=["force"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda magnetic_moment: 1.0,
            causal_direction=[("magnetic_moment", "force")],
        ),
        PhysicsLaw(
            name="ElectricPolarization", domain="electromagnetism",
            latex=r"P = ε₀χE",
            inputs=["electric_field"], outputs=["polarization"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda electric_field: 1.0,
            causal_direction=[("electric_field", "polarization")],
        ),
        PhysicsLaw(
            name="PolarizationToRefractiveIndex", domain="optics",
            latex=r"n = √(1+χ)",
            inputs=["polarization"], outputs=["refractive_index"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda polarization: 1.0,
            causal_direction=[("polarization", "refractive_index")],
        ),
        PhysicsLaw(
            name="CurieLaw", domain="condensed_matter",
            latex=r"M = C·B/T",
            inputs=["magnetic_field", "temperature"], outputs=["magnetization"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda magnetic_field, temperature: 1.0,
            causal_direction=[("magnetic_field", "magnetization"),
                            ("temperature", "magnetization")],
        ),
        PhysicsLaw(
            name="MagnetizationPhaseTransition", domain="thermodynamics",
            latex=r"M→0 at T_C",
            inputs=["magnetization"], outputs=["phase"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda magnetization: 1.0,
            causal_direction=[("magnetization", "phase")],
        ),
        
        # ═══ 波动物理量子桥 ═══
        PhysicsLaw(
            name="WaveNumberMomentum", domain="quantum",
            latex=r"p = ħk",
            inputs=["wave_number"], outputs=["momentum"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda wave_number: 1.0,
            causal_direction=[("wave_number", "momentum")],
        ),
        PhysicsLaw(
            name="FrequencyPhotonEnergy", domain="quantum",
            latex=r"E = hν",
            inputs=["frequency"], outputs=["photon_energy"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda frequency: 1.0,
            causal_direction=[("frequency", "photon_energy")],
        ),
        
        # ═══ 额外桥梁 ═══
        PhysicsLaw(
            name="RefractiveIndexToWavelength", domain="optics",
            latex=r"n → λ",
            inputs=["refractive_index"], outputs=["wavelength"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda refractive_index: 1.0,
            causal_direction=[("refractive_index", "wavelength")],
        ),
        PhysicsLaw(
            name="OpticalGapToWavelength", domain="optics",
            latex=r"E_g = hc/λ",
            inputs=["optical_gap"], outputs=["wavelength"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda optical_gap: 1.0,
            causal_direction=[("optical_gap", "wavelength")],
        ),
        PhysicsLaw(
            name="EntropyToInformation", domain="quantum",
            latex=r"S = -k Σ p_i ln p_i",
            inputs=["entropy"], outputs=["information_erased"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda entropy: 1.0,
            causal_direction=[("entropy", "information_erased")],
        ),

        # ═══ 规范场/几何统一 ═══
        PhysicsLaw(
            name="GaugeFieldAsConnection", domain="gauge_geometry",
            latex=r"A_μ → ω",
            inputs=["gauge_field"], outputs=["connection_1form"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda gauge_field: 1.0,
            causal_direction=[("gauge_field", "connection_1form")],
        ),
        PhysicsLaw(
            name="ConnectionToCurvature", domain="gauge_geometry",
            latex=r"F = dA + A∧A",
            inputs=["connection_1form"], outputs=["curvature_2form"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda connection_1form: 1.0,
            causal_direction=[("connection_1form", "curvature_2form")],
        ),
        PhysicsLaw(
            name="CurvatureToYangMillsAction", domain="gauge_geometry",
            latex=r"S_YM = ∫ tr(F∧*F)",
            inputs=["curvature_2form"], outputs=["yang_mills_action"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda curvature_2form: 1.0,
            causal_direction=[("curvature_2form", "yang_mills_action")],
        ),
        PhysicsLaw(
            name="YangMillsToFieldEquation", domain="gauge_geometry",
            latex=r"δS=0 → D*F=0",
            inputs=["yang_mills_action"], outputs=["gauge_field_equation"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda yang_mills_action: 1.0,
            causal_direction=[("yang_mills_action", "gauge_field_equation")],
        ),
        PhysicsLaw(
            name="SymmetryDefinesBundle", domain="gauge_geometry",
            latex=r"G → P(M,G)",
            inputs=["symmetry_group"], outputs=["principal_bundle"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda symmetry_group: 1.0,
            causal_direction=[("symmetry_group", "principal_bundle")],
        ),
        PhysicsLaw(
            name="BundleToConnection", domain="gauge_geometry",
            latex=r"P(M,G) → ω",
            inputs=["principal_bundle"], outputs=["connection_1form"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda principal_bundle: 1.0,
            causal_direction=[("principal_bundle", "connection_1form")],
        ),
        PhysicsLaw(
            name="ConnectionToCovariantDerivative", domain="gauge_geometry",
            latex=r"D_μ = ∂_μ + A_μ",
            inputs=["connection_1form"], outputs=["covariant_derivative"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda connection_1form: 1.0,
            causal_direction=[("connection_1form", "covariant_derivative")],
        ),
        PhysicsLaw(
            name="ConnectionToWilsonLoop", domain="gauge_geometry",
            latex=r"W = P exp(i∮A)",
            inputs=["connection_1form"], outputs=["wilson_loop"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda connection_1form: 1.0,
            causal_direction=[("connection_1form", "wilson_loop")],
        ),
        PhysicsLaw(
            name="WilsonToObservable", domain="gauge_geometry",
            latex=r"W → observable",
            inputs=["wilson_loop"], outputs=["gauge_invariant_observable"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda wilson_loop: 1.0,
            causal_direction=[("wilson_loop", "gauge_invariant_observable")],
        ),
        PhysicsLaw(
            name="CurvatureToChernClass", domain="gauge_geometry",
            latex=r"tr(F∧F) → c₂",
            inputs=["curvature_2form"], outputs=["chern_class"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda curvature_2form: 1.0,
            causal_direction=[("curvature_2form", "chern_class")],
        ),
        PhysicsLaw(
            name="ChernToInstanton", domain="gauge_geometry",
            latex=r"c₂ → instanton_number",
            inputs=["chern_class"], outputs=["instanton_number"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda chern_class: 1.0,
            causal_direction=[("chern_class", "instanton_number")],
        ),
        PhysicsLaw(
            name="InstantonToTunneling", domain="gauge_geometry",
            latex=r"instanton → tunneling",
            inputs=["instanton_number"], outputs=["quantum_tunneling"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda instanton_number: 1.0,
            causal_direction=[("instanton_number", "quantum_tunneling")],
        ),
        PhysicsLaw(
            name="ActionToPathIntegral", domain="gauge_geometry",
            latex=r"S → ∫Dφ e^{iS}",
            inputs=["yang_mills_action"], outputs=["path_integral_measure"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda yang_mills_action: 1.0,
            causal_direction=[("yang_mills_action", "path_integral_measure")],
        ),
        PhysicsLaw(
            name="PathIntegralToAmplitude", domain="gauge_geometry",
            latex=r"∫Dφ e^{iS} → ⟨out|in⟩",
            inputs=["path_integral_measure"], outputs=["quantum_amplitude"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda path_integral_measure: 1.0,
            causal_direction=[("path_integral_measure", "quantum_amplitude")],
        ),
        PhysicsLaw(
            name="AnomalyFromMeasure", domain="gauge_geometry",
            latex=r"Dφ not invariant → anomaly",
            inputs=["path_integral_measure"], outputs=["anomaly"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda path_integral_measure: 1.0,
            causal_direction=[("path_integral_measure", "anomaly")],
        ),
        PhysicsLaw(
            name="BRSTSymmetry", domain="gauge_geometry",
            latex=r"FP determinant → BRST",
            inputs=["gauge_fixing"], outputs=["brst_symmetry"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda gauge_fixing: 1.0,
            causal_direction=[("gauge_fixing", "brst_symmetry")],
        ),
        PhysicsLaw(
            name="ChernClassToSimonsForm", domain="gauge_geometry",
            latex=r"c₂ → CS₃",
            inputs=["chern_class"], outputs=["chern_simons_form"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda chern_class: 1.0,
            causal_direction=[("chern_class", "chern_simons_form")],
        ),

        # ═══ GR ↔ 规范场统一桥 ═══
        PhysicsLaw(
            name="GRCurvatureAsGaugeCurvature", domain="gauge_geometry",
            latex=r"Riemann ∼ gauge curvature",
            inputs=["spacetime_curvature"], outputs=["curvature_2form"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda spacetime_curvature: 1.0,
            causal_direction=[("spacetime_curvature", "curvature_2form")],
        ),
        PhysicsLaw(
            name="HilbertActionAsYangMills", domain="gauge_geometry",
            latex=r"∫R√g ∼ ∫tr(F∧*F)",
            inputs=["hilbert_action"], outputs=["yang_mills_action"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda hilbert_action: 1.0,
            causal_direction=[("hilbert_action", "yang_mills_action")],
        ),
        PhysicsLaw(
            name="ActionToSpacetime", domain="gauge_geometry",
            latex=r"S_YM + S_EH → unified_geometric_action",
            inputs=["yang_mills_action"], outputs=["unified_geometric_action"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda yang_mills_action: 1.0,
            causal_direction=[("yang_mills_action", "unified_geometric_action")],
        ),
        PhysicsLaw(
            name="DiracOperatorNeedsConnection", domain="gauge_geometry",
            latex=r"D̸ = γ^μ D_μ",
            inputs=["dirac_operator"], outputs=["connection_1form"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda dirac_operator: 1.0,
            causal_direction=[("dirac_operator", "connection_1form")],
        ),
        PhysicsLaw(
            name="MatterFieldAsSection", domain="gauge_geometry",
            latex=r"ψ: M → V",
            inputs=["matter_field"], outputs=["fiber_section"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda matter_field: 1.0,
            causal_direction=[("matter_field", "fiber_section")],
        ),

        # ═══ 量子化 ═══
        PhysicsLaw(
            name="ActionToQuantum", domain="quantum",
            latex=r"S → Z = ∫Dφ e^{iS/ħ}",
            inputs=["action"], outputs=["path_integral_measure"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda action: 1.0,
            causal_direction=[("action", "path_integral_measure")],
        ),
        PhysicsLaw(
            name="LagrangianToAction", domain="quantum",
            latex=r"L → S = ∫L dt",
            inputs=["lagrangian"], outputs=["action"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda lagrangian: 1.0,
            causal_direction=[("lagrangian", "action")],
        ),
        
        # ═══ 🔬 经典物理实验: 费曼的现实锚点 ═══
        # 光电效应 (Einstein 1905)
        PhysicsLaw(
            name="photoelectric_effect", domain="quantum",
            latex=r"light → electron emission, E=hf-φ",
            inputs=[], outputs=["photoelectric_effect"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("energy", "photoelectric_effect"), ("frequency", "photoelectric_effect"),
                            ("planck_constant", "photoelectric_effect"), ("wavelength", "photoelectric_effect")],
        ),
        # 双缝干涉 (Young 1801)
        PhysicsLaw(
            name="double_slit", domain="optics",
            latex=r"interference pattern from two coherent sources",
            inputs=[], outputs=["double_slit"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("wave_function", "double_slit"), ("wavelength", "double_slit"),
                            ("frequency", "double_slit"), ("distance", "double_slit")],
        ),
        # 黑体辐射 (Planck 1900)
        PhysicsLaw(
            name="blackbody_radiation", domain="thermodynamics",
            latex=r"E(ν,T) = hν / (e^{hν/kT}-1)",
            inputs=[], outputs=["blackbody_radiation"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("temperature", "blackbody_radiation"), ("energy", "blackbody_radiation"),
                            ("frequency", "blackbody_radiation"), ("wavelength", "blackbody_radiation")],
        ),
        # 康普顿散射 (Compton 1923)
        PhysicsLaw(
            name="compton_scattering", domain="quantum",
            latex=r"Δλ = h/mc · (1-cosθ)",
            inputs=[], outputs=["compton_scattering"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("energy", "compton_scattering"), ("momentum", "compton_scattering"),
                            ("wavelength", "compton_scattering"), ("mass", "compton_scattering")],
        ),
        # 卢瑟福金箔 (Rutherford 1911)
        PhysicsLaw(
            name="rutherford_gold_foil", domain="modern",
            latex=r"α particles deflected by nucleus",
            inputs=[], outputs=["rutherford_gold_foil"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("charge", "rutherford_gold_foil"), ("mass", "rutherford_gold_foil"),
                            ("force", "rutherford_gold_foil"), ("acceleration", "rutherford_gold_foil")],
        ),
        # 迈克尔逊-莫雷 (Michelson 1887)
        PhysicsLaw(
            name="michelson_morley", domain="optics",
            latex=r"null result → no aether, constant c",
            inputs=[], outputs=["michelson_morley"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("speed_of_light", "michelson_morley"), ("velocity", "michelson_morley"),
                            ("lorentz", "michelson_morley"), ("time", "michelson_morley")],
        ),
        # 伽利略斜面 (Galileo 1604)
        PhysicsLaw(
            name="galileo_inclined_plane", domain="mechanics",
            latex=r"uniform acceleration on incline",
            inputs=[], outputs=["galileo_inclined_plane"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("acceleration", "galileo_inclined_plane"), ("velocity", "galileo_inclined_plane"),
                            ("time", "galileo_inclined_plane"), ("distance", "galileo_inclined_plane"),
                            ("force", "galileo_inclined_plane")],
        ),
        # 开普勒第三定律 (Kepler 1619)
        PhysicsLaw(
            name="kepler_third_law", domain="mechanics",
            latex=r"T² ∝ a³",
            inputs=[], outputs=["kepler_third_law"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("mass", "kepler_third_law"), ("angular_momentum", "kepler_third_law"),
                            ("time", "kepler_third_law"), ("distance", "kepler_third_law"),
                            ("force", "kepler_third_law")],
        ),
        # 法拉第电磁感应 (Faraday 1831)
        PhysicsLaw(
            name="faraday_induction", domain="electromagnetism",
            latex=r"∇×E = -∂B/∂t",
            inputs=[], outputs=["faraday_induction"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("magnetic_field", "faraday_induction"), ("electric_field", "faraday_induction"),
                            ("current", "faraday_induction"), ("energy", "faraday_induction")],
        ),
        # 欧姆定律 (Ohm 1827)
        PhysicsLaw(
            name="ohm_law_experiment", domain="electromagnetism",
            latex=r"V = IR",
            inputs=[], outputs=["ohm_law_experiment"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("voltage", "ohm_law_experiment"), ("current", "ohm_law_experiment"),
                            ("resistance", "ohm_law_experiment")],
        ),
        # 玻义耳定律 (Boyle 1662)
        PhysicsLaw(
            name="boyle_law", domain="thermodynamics",
            latex=r"PV = constant at constant T",
            inputs=[], outputs=["boyle_law"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("pressure", "boyle_law"), ("volume", "boyle_law"), ("temperature", "boyle_law")],
        ),
        # 卡诺循环 (Carnot 1824)
        PhysicsLaw(
            name="carnot_cycle", domain="thermodynamics",
            latex=r"η = 1 - T_c/T_h",
            inputs=[], outputs=["carnot_cycle"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("temperature", "carnot_cycle"), ("energy", "carnot_cycle"),
                            ("entropy", "carnot_cycle"), ("work", "carnot_cycle"), ("volume", "carnot_cycle")],
        ),
        # 布朗运动 (Brown 1827 / Einstein 1905)
        PhysicsLaw(
            name="brownian_motion", domain="thermodynamics",
            latex=r"random walk of particles in fluid",
            inputs=[], outputs=["brownian_motion"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("temperature", "brownian_motion"), ("energy", "brownian_motion"),
                            ("mass", "brownian_motion"), ("momentum", "brownian_motion")],
        ),
        # 斯特恩-格拉赫 (Stern-Gerlach 1922)
        PhysicsLaw(
            name="stern_gerlach_experiment", domain="quantum",
            latex=r"spin quantization → beam split",
            inputs=[], outputs=["stern_gerlach_experiment"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("spin", "stern_gerlach_experiment"), ("magnetic_field", "stern_gerlach_experiment"),
                            ("angular_momentum", "stern_gerlach_experiment")],
        ),
        # 塞曼效应 (Zeeman 1896)
        PhysicsLaw(
            name="zeeman_effect", domain="electromagnetism",
            latex=r"magnetic field splits spectral lines",
            inputs=[], outputs=["zeeman_effect"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("magnetic_field", "zeeman_effect"), ("energy", "zeeman_effect"),
                            ("frequency", "zeeman_effect"), ("wavelength", "zeeman_effect")],
        ),
        # 多普勒效应 (Doppler 1842)
        PhysicsLaw(
            name="doppler_effect", domain="wave",
            latex=r"f' = f · (c±v_r)/(c∓v_s)",
            inputs=[], outputs=["doppler_effect"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("frequency", "doppler_effect"), ("velocity", "doppler_effect"),
                            ("wavelength", "doppler_effect"), ("time", "doppler_effect")],
        ),
        # 库仑定律 (Coulomb 1785)
        PhysicsLaw(
            name="coulomb_law_experiment", domain="electromagnetism",
            latex=r"F = k·q₁q₂/r²",
            inputs=[], outputs=["coulomb_law_experiment"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("charge", "coulomb_law_experiment"), ("force", "coulomb_law_experiment"),
                            ("distance", "coulomb_law_experiment"), ("electric_field", "coulomb_law_experiment")],
        ),
        # 单摆 (Galileo)
        PhysicsLaw(
            name="pendulum_motion", domain="mechanics",
            latex=r"T = 2π√(L/g)",
            inputs=[], outputs=["pendulum_motion"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("time", "pendulum_motion"), ("acceleration", "pendulum_motion"),
                            ("distance", "pendulum_motion"), ("velocity", "pendulum_motion"),
                            ("force", "pendulum_motion")],
        ),
        # 阿基米德原理 (Archimedes)
        PhysicsLaw(
            name="archimedes_principle", domain="mechanics",
            latex=r"F_b = ρgV",
            inputs=[], outputs=["archimedes_principle"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("density", "archimedes_principle"), ("volume", "archimedes_principle"),
                            ("force", "archimedes_principle"), ("pressure", "archimedes_principle")],
        ),
        # 伯努利原理 (Bernoulli 1738)
        PhysicsLaw(
            name="bernoulli_principle", domain="mechanics",
            latex=r"P + ½ρv² + ρgh = const",
            inputs=[], outputs=["bernoulli_principle"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("pressure", "bernoulli_principle"), ("velocity", "bernoulli_principle"),
                            ("energy", "bernoulli_principle"), ("density", "bernoulli_principle"),
                            ("force", "bernoulli_principle")],
        ),
        # 超导 (Onnes 1911)
        PhysicsLaw(
            name="superconductivity_onset", domain="condensed_matter",
            latex=r"R→0 below T_c",
            inputs=[], outputs=["superconductivity_onset"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("temperature", "superconductivity_onset"), ("resistance", "superconductivity_onset"),
                            ("energy", "superconductivity_onset"), ("current", "superconductivity_onset")],
        ),
        # 衍射光栅
        PhysicsLaw(
            name="diffraction_grating", domain="optics",
            latex=r"nλ = d·sinθ",
            inputs=[], outputs=["diffraction_grating"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("wavelength", "diffraction_grating"), ("frequency", "diffraction_grating"),
                            ("distance", "diffraction_grating"), ("wave_function", "diffraction_grating")],
        ),
        # 能量均分定理 (Boltzmann)
        PhysicsLaw(
            name="equipartition_theorem", domain="thermodynamics",
            latex=r"E = ½kT per degree of freedom",
            inputs=[], outputs=["equipartition_theorem"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("temperature", "equipartition_theorem"), ("energy", "equipartition_theorem"),
                            ("frequency", "equipartition_theorem")],
        ),
        # 牛顿万有引力
        PhysicsLaw(
            name="universal_gravitation", domain="mechanics",
            latex=r"F = G·m₁m₂/r²",
            inputs=[], outputs=["universal_gravitation"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("mass", "universal_gravitation"), ("force", "universal_gravitation"),
                            ("acceleration", "universal_gravitation"), ("distance", "universal_gravitation"),
                            ("spacetime_curvature", "universal_gravitation")],
        ),
        
        # ═══ 🏛 哲学思想实验: 费曼的深层结构 ═══
        # 爱因斯坦电梯 (等价原理)
        PhysicsLaw(
            name="einstein_elevator", domain="philosophy",
            latex=r"gravity ≡ acceleration (equivalence)",
            inputs=[], outputs=["einstein_elevator"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("mass", "einstein_elevator"), ("acceleration", "einstein_elevator"),
                            ("spacetime_curvature", "einstein_elevator")],
        ),
        # 薛定谔猫 (观测者问题)
        PhysicsLaw(
            name="schrodinger_cat", domain="philosophy",
            latex=r"cat alive + dead until observed",
            inputs=[], outputs=["schrodinger_cat"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("wave_function", "schrodinger_cat"), ("measurement", "schrodinger_cat")],
        ),
        # EPR 佯谬 (局域性)
        PhysicsLaw(
            name="epr_paradox", domain="philosophy",
            latex=r"spooky action at a distance",
            inputs=[], outputs=["epr_paradox"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("spin", "epr_paradox"), ("wave_function", "epr_paradox"),
                            ("speed_of_light", "epr_paradox")],
        ),
        # 麦克斯韦妖 (信息与熵)
        PhysicsLaw(
            name="maxwell_demon", domain="philosophy",
            latex=r"information = thermodynamic cost",
            inputs=[], outputs=["maxwell_demon"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("entropy", "maxwell_demon"), ("temperature", "maxwell_demon"),
                            ("energy", "maxwell_demon")],
        ),
        # 双生子佯谬 (时间相对性)
        PhysicsLaw(
            name="twin_paradox", domain="philosophy",
            latex=r"moving twin ages slower",
            inputs=[], outputs=["twin_paradox"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("time", "twin_paradox"), ("velocity", "twin_paradox"),
                            ("speed_of_light", "twin_paradox"), ("lorentz", "twin_paradox")],
        ),
        # 诺特定理 (对称性与守恒)
        PhysicsLaw(
            name="noether_theorem", domain="philosophy",
            latex=r"symmetry → conservation law",
            inputs=[], outputs=["noether_theorem"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("action", "noether_theorem"), ("energy", "noether_theorem"),
                            ("momentum", "noether_theorem"), ("time", "noether_theorem")],
        ),
        # 费曼路径积分 (所有历史)
        PhysicsLaw(
            name="feynman_path_integral", domain="philosophy",
            latex=r"particle takes every path",
            inputs=[], outputs=["feynman_path_integral"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("action", "feynman_path_integral"), ("wave_function", "feynman_path_integral"),
                            ("time", "feynman_path_integral")],
        ),
        # 惠勒延迟选择 (逆因果)
        PhysicsLaw(
            name="wheeler_delayed_choice", domain="philosophy",
            latex=r"now affects past?",
            inputs=[], outputs=["wheeler_delayed_choice"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("wave_function", "wheeler_delayed_choice"), ("time", "wheeler_delayed_choice")],
        ),
        # 互补性原理 (波粒二象性)
        PhysicsLaw(
            name="complementarity", domain="philosophy",
            latex=r"wave and particle are complementary",
            inputs=[], outputs=["complementarity"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("wave_function", "complementarity"), ("momentum", "complementarity"),
                            ("wavelength", "complementarity")],
        ),
        # 对应原理 (涌现)
        PhysicsLaw(
            name="correspondence_principle", domain="philosophy",
            latex=r"quantum → classical in large-n limit",
            inputs=[], outputs=["correspondence_principle"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("quantum", "correspondence_principle"), ("mechanics", "correspondence_principle"),
                            ("energy", "correspondence_principle")],
        ),
        # 拉普拉斯妖 (决定论)
        PhysicsLaw(
            name="laplace_demon", domain="philosophy",
            latex=r"if you know all positions+velocities...",
            inputs=[], outputs=["laplace_demon"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("mass", "laplace_demon"), ("velocity", "laplace_demon"),
                            ("momentum", "laplace_demon"), ("time", "laplace_demon")],
        ),
        # 牛顿水桶 (绝对空间)
        PhysicsLaw(
            name="newtons_bucket", domain="philosophy",
            latex=r"rotation is absolute, not relative",
            inputs=[], outputs=["newtons_bucket"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("acceleration", "newtons_bucket"), ("spacetime_curvature", "newtons_bucket"),
                            ("force", "newtons_bucket")],
        ),
        # 伽利略船 (相对性)
        PhysicsLaw(
            name="galileos_ship", domain="philosophy",
            latex=r"motion is undetectable in inertial frame",
            inputs=[], outputs=["galileos_ship"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("velocity", "galileos_ship"), ("acceleration", "galileos_ship"),
                            ("force", "galileos_ship")],
        ),
        # 奥卡姆剃刀 (简洁性)
        PhysicsLaw(
            name="ockham_razor", domain="philosophy",
            latex=r"simplest explanation is best",
            inputs=[], outputs=["ockham_razor"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("entropy", "ockham_razor"), ("action", "ockham_razor")],
        ),
        # 人择原理 (观测者选择)
        PhysicsLaw(
            name="anthropic_principle", domain="philosophy",
            latex=r"we see what allows us to exist",
            inputs=[], outputs=["anthropic_principle"],
            constraint_type=ConstraintType.DAG_EDGE,
            formula=lambda: 1.0,
            causal_direction=[("time", "anthropic_principle"), ("energy", "anthropic_principle"),
                            ("temperature", "anthropic_principle")],
        ),
    ]
    
    added = 0
    for law in bridges:
        if law.name not in {l.name for l in library._laws}:
            library._laws.append(law)
            added += 1
    
    return added
