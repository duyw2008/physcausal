"""
天文/宇宙学定律库 — 补充费曼脑天文域知识
覆盖：观测宇宙学、引力透镜、恒星天体物理、巡天技术
"""
import math
from physics.laws import PhysicsLaw, ConstraintType

ASTRONOMY_LAWS = [
    # ═══ 观测宇宙学 ═══
    PhysicsLaw(
        name="HubbleLaw", domain="astronomy",
        latex=r"v = H_0 d",
        inputs=["distance", "hubble_constant"],
        outputs=["recession_velocity"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda distance, hubble_constant: hubble_constant * distance,
        causal_direction=[
            ("distance", "redshift"),
            ("redshift", "recession_velocity"),
        ],
    ),
    PhysicsLaw(
        name="CosmicExpansion", domain="astronomy",
        latex=r"a(t) \\text{{ evolves via Friedmann eq}}",
        inputs=["expansion_rate", "scale_factor"],
        outputs=["redshift"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda expansion_rate, scale_factor: (1 / scale_factor) - 1,
        causal_direction=[
            ("scale_factor", "redshift"),
            ("scale_factor", "cosmic_distance"),
            ("expansion_rate", "scale_factor"),
        ],
    ),
    PhysicsLaw(
        name="CosmologicalRedshift", domain="astronomy",
        latex=r"1+z = a_0/a",
        inputs=["scale_factor_now", "scale_factor_emit"],
        outputs=["redshift"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda scale_factor_now, scale_factor_emit: (scale_factor_now / scale_factor_emit) - 1 if scale_factor_emit != 0 else 0,
        causal_direction=[
            ("cosmic_expansion", "wavelength_shift"),
            ("redshift", "wavelength"),
            ("scale_factor", "photon_energy"),
        ],
    ),

    # ═══ 引力透镜 ═══
    PhysicsLaw(
        name="GravitationalLensing", domain="astronomy",
        latex=r"\\alpha = 4GM/(c^2 b)",
        inputs=["lens_mass", "impact_parameter", "G", "c"],
        outputs=["deflection_angle"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda lens_mass, impact_parameter, G=6.674e-11, c=3e8: 
            4 * G * lens_mass / (c * c * max(impact_parameter, 1e-10)),
        causal_direction=[
            ("mass_distribution", "light_deflection"),
            ("mass_distribution", "image_shear"),
            ("mass_distribution", "magnification"),
            ("image_shear", "shear_map"),
        ],
    ),
    PhysicsLaw(
        name="WeakLensing", domain="astronomy",
        latex=r"\\gamma \\propto \\nabla_\\perp \\nabla_\\perp \\Phi",
        inputs=["gravitational_potential", "source_distance"],
        outputs=["weak_lensing_shear"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda gravitational_potential, source_distance: 
            gravitational_potential * source_distance,
        causal_direction=[
            ("large_scale_structure", "weak_lensing_shear"),
            ("dark_matter_distribution", "weak_lensing_shear"),
            ("weak_lensing_shear", "mass_reconstruction"),
            ("weak_lensing_shear", "dark_energy_constraints"),
        ],
    ),
    PhysicsLaw(
        name="EinsteinRing", domain="astronomy",
        latex=r"\\theta_E = \\sqrt{{4GM D_{{ls}} / (c^2 D_l D_s)}}",
        inputs=["lens_mass", "D_ls", "D_l", "D_s"],
        outputs=["einstein_radius"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda lens_mass, D_ls, D_l, D_s, G=6.674e-11, c=3e8:
            math.sqrt(4 * G * lens_mass * D_ls / (c * c * D_l * max(D_s, 1))),
        causal_direction=[
            ("lens_source_alignment", "einstein_ring"),
            ("lens_mass", "einstein_radius"),
        ],
    ),

    # ═══ 暗物质/暗能量 ═══
    PhysicsLaw(
        name="GalaxyRotationCurve", domain="astronomy",
        latex=r"v^2 = GM(r)/r",
        inputs=["enclosed_mass", "radius", "G"],
        outputs=["rotation_velocity"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda enclosed_mass, radius, G=6.674e-11:
            math.sqrt(G * enclosed_mass / max(radius, 1e-10)),
        causal_direction=[
            ("dark_matter_halo", "rotation_curve"),
            ("rotation_curve", "dark_matter_mass"),
            ("galaxy_mass", "rotation_velocity"),
        ],
    ),
    PhysicsLaw(
        name="DarkEnergyEOS", domain="astronomy",
        latex=r"w = p/\\rho",
        inputs=["dark_energy_pressure", "dark_energy_density"],
        outputs=["equation_of_state_w"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda dark_energy_pressure, dark_energy_density:
            dark_energy_pressure / max(dark_energy_density, 1e-10),
        causal_direction=[
            ("dark_energy_density", "cosmic_acceleration"),
            ("equation_of_state_w", "expansion_history"),
            ("expansion_history", "distance_redshift_relation"),
        ],
    ),
    PhysicsLaw(
        name="StructureFormation", domain="astronomy",
        latex=r"\\delta \\propto a",
        inputs=["initial_fluctuations", "scale_factor", "growth_factor"],
        outputs=["large_scale_structure"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda initial_fluctuations, scale_factor, growth_factor:
            initial_fluctuations * scale_factor * growth_factor,
        causal_direction=[
            ("dark_matter_halo", "galaxy_formation"),
            ("dark_matter_halo", "large_scale_structure"),
            ("initial_fluctuations", "large_scale_structure"),
            ("large_scale_structure", "galaxy_clustering"),
        ],
    ),

    # ═══ 超新星 ═══
    PhysicsLaw(
        name="TypeIaSupernova", domain="astronomy",
        latex=r"L \\approx const \\times M_{{Ni}}",
        inputs=["nickel_mass", "rise_time"],
        outputs=["peak_luminosity"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda nickel_mass, rise_time:
            nickel_mass * 2e43 / max(rise_time, 0.1),
        causal_direction=[
            ("white_dwarf_accretion", "chandrasekhar_limit"),
            ("chandrasekhar_limit", "supernova_explosion"),
            ("supernova_lightcurve", "peak_luminosity"),
            ("peak_luminosity", "distance_measurement"),
        ],
    ),
    PhysicsLaw(
        name="StellarNucleosynthesis", domain="astronomy",
        latex=r"\\text{{fusion rate}} \\propto T^{{...}}",
        inputs=["stellar_core_temperature", "stellar_mass"],
        outputs=["element_abundance"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda stellar_core_temperature, stellar_mass:
            stellar_core_temperature * math.log(max(stellar_mass, 1)),
        causal_direction=[
            ("stellar_core_temperature", "nuclear_fusion"),
            ("nuclear_fusion", "element_abundance"),
            ("stellar_mass", "fusion_products"),
        ],
    ),
    PhysicsLaw(
        name="TullyFisher", domain="astronomy",
        latex=r"L \\propto v_{{rot}}^4",
        inputs=["rotation_velocity"],
        outputs=["galaxy_luminosity"],
        constraint_type=ConstraintType.DAG_EDGE,
        formula=lambda rotation_velocity: rotation_velocity ** 4,
        causal_direction=[
            ("rotation_velocity", "galaxy_luminosity"),
            ("galaxy_luminosity", "distance_indicator"),
        ],
    ),

    # ═══ 巡天技术 ═══
    PhysicsLaw(
        name="WideFieldSurvey", domain="astronomy",
        latex=r"N \\propto \\Omega t_{{exp}}",
        inputs=["field_of_view", "exposure_time"],
        outputs=["source_detection_rate"],
        constraint_type=ConstraintType.DAG_EDGE,
        formula=lambda field_of_view, exposure_time:
            field_of_view * exposure_time,
        causal_direction=[
            ("field_of_view", "sky_coverage"),
            ("sky_coverage", "source_detection_rate"),
            ("exposure_time", "depth_limit"),
            ("depth_limit", "redshift_reach"),
        ],
    ),
    PhysicsLaw(
        name="PhotometricRedshift", domain="astronomy",
        latex=r"z_{{phot}} = f(m_1, m_2, \\ldots, m_N)",
        inputs=["multi_band_magnitudes"],
        outputs=["photometric_redshift"],
        constraint_type=ConstraintType.DAG_EDGE,
        formula=lambda multi_band_magnitudes: multi_band_magnitudes * 0.1,
        causal_direction=[
            ("multi_band_photometry", "spectral_energy_distribution"),
            ("spectral_energy_distribution", "photometric_redshift"),
            ("photometric_redshift", "large_scale_structure_map"),
        ],
    ),
    PhysicsLaw(
        name="TimeDomainSurvey", domain="astronomy",
        latex=r"\\text{{detect}} \\propto \\text{{cadence}}^{{-1}}",
        inputs=["cadence", "depth"],
        outputs=["transient_detection_rate"],
        constraint_type=ConstraintType.DAG_EDGE,
        formula=lambda cadence, depth: depth / max(cadence, 0.01),
        causal_direction=[
            ("repeated_observations", "transient_detection"),
            ("cadence", "transient_sensitivity"),
            ("transient_detection", "supernova_discovery"),
            ("transient_detection", "variable_star_catalog"),
        ],
    ),
    PhysicsLaw(
        name="CMB", domain="astronomy",
        latex=r"\\Delta T/T \\sim 10^{{-5}}",
        inputs=["cmb_temperature_mean"],
        outputs=["cmb_fluctuation_amplitude"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda cmb_temperature_mean: cmb_temperature_mean * 1e-5,
        causal_direction=[
            ("recombination", "cmb_release"),
            ("cmb_temperature_fluctuations", "primordial_fluctuations"),
            ("cmb_polarization", "gravitational_wave_imprint"),
            ("cmb_anisotropy", "cosmological_parameters"),
        ],
    ),

    # ═══ 引力波天文 ═══
    PhysicsLaw(
        name="GWChirpMass", domain="astronomy",
        latex=r"\\mathcal{{M}} = (m_1 m_2)^{{3/5}}/(m_1+m_2)^{{1/5}}",
        inputs=["m1", "m2"],
        outputs=["chirp_mass"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda m1, m2:
            (m1 * m2) ** 0.6 / ((m1 + m2) ** 0.2) if (m1 + m2) > 0 else 0,
        causal_direction=[
            ("binary_merger", "gravitational_wave_signal"),
            ("gravitational_wave_signal", "chirp_mass"),
            ("chirp_mass", "luminosity_distance"),
            ("waveform", "source_parameters"),
        ],
    ),

    # ═══ 距离阶梯 ═══
    PhysicsLaw(
        name="CosmicDistanceLadder", domain="astronomy",
        latex=r"d = 10^{{(m-M+5)/5}}",
        inputs=["apparent_magnitude", "absolute_magnitude"],
        outputs=["luminosity_distance"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda apparent_magnitude, absolute_magnitude:
            10 ** ((apparent_magnitude - absolute_magnitude + 5) / 5),
        causal_direction=[
            ("parallax", "nearby_distance"),
            ("cepheid_period", "luminosity"),
            ("luminosity", "distance"),
            ("standard_candle", "cosmic_distance"),
        ],
    ),
]
