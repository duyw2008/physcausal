#!/usr/bin/env python3
"""费曼脑论文摄入 — 从 28 篇新论文摘要提取因果边, 写入 feed_queue.jsonl (edge 类型).

数据源: arXiv API 摘要 (web_extract 未配置, 用 export.arxiv.org 直读).
每条边: (arxiv_id, src, dst, confidence) → FeedQueue.feed_edge
"""
import sys, os, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from meta_cognition.feed_queue import FeedQueue

# (arxiv_id, src, dst, confidence)
EDGES = [
    # 1. 2608.14541v1 — Quantum Black Hole Microstate (bulk path integral)
    ("2608.14541v1", "chern_simons_wilson_line", "heavy_virasoro_primary", 0.8),
    ("2608.14541v1", "drinfeld_sokolov_reduction", "virasoro_module", 0.9),
    ("2608.14541v1", "temperature_chemical_potential", "holonomy_saddle", 0.8),
    ("2608.14541v1", "heavy_primary_density", "defect_saddle", 0.7),
    ("2608.14541v1", "modular_invariance", "cardy_density", 0.8),

    # 2. 2608.14538v1 — Vector-Like Fermions at FCC-ee
    ("2608.14538v1", "vector_like_fermion_yukawa", "higgs_strahlung_cross_section", 0.8),
    ("2608.14538v1", "vector_like_fermion_mixing", "higgs_strahlung_cross_section", 0.7),
    ("2608.14538v1", "vector_like_fermion_loop", "oblique_parameters", 0.8),
    ("2608.14538v1", "yukawa_coupling", "higgs_diphoton_rate", 0.7),
    ("2608.14538v1", "electroweak_precision_bound", "observable_shift", 0.7),

    # 3. 2608.14523v1 — Okinawa Lectures on Entropy
    ("2608.14523v1", "classical_probability_theory", "shannon_entropy", 0.8),
    ("2608.14523v1", "large_deviation_theory", "classical_entropy", 0.8),
    ("2608.14523v1", "statistical_hypothesis_testing", "quantum_entropy", 0.8),
    ("2608.14523v1", "von_neumann_algebra", "relative_entropy", 0.8),
    ("2608.14523v1", "modular_theory", "araki_uhlmann_entropy", 0.8),

    # 4. 2608.14512v1 — Non-Perturbative Classical Double Copy
    ("2608.14512v1", "biadjoint_scalar_theory", "yang_mills_theory", 0.8),
    ("2608.14512v1", "yang_mills_theory", "general_relativity", 0.8),
    ("2608.14512v1", "scalar_seed", "conformal_metric", 0.9),
    ("2608.14512v1", "trace_free_einstein_equation", "gravity_yang_mills_source_relation", 0.7),
    ("2608.14512v1", "coupling_identification", "common_equation_of_motion", 0.8),

    # 5. 2608.14463v1 — scalar DBI black hole analogue
    ("2608.14463v1", "dirac_born_infeld_theory", "black_hole_analogue", 0.8),
    ("2608.14463v1", "event_horizon", "zero_information_propagation_speed", 0.8),
    ("2608.14463v1", "static_perturbation", "love_number", 0.9),
    ("2608.14463v1", "dynamic_perturbation", "quasi_normal_modes", 0.8),
    ("2608.14463v1", "background_geometry", "high_pass_filter", 0.7),

    # 6. 2608.14451v1 — Four-point functions, Twistors, Supersymmetry
    ("2608.14451v1", "grassmannian_minors", "correlation_function", 0.8),
    ("2608.14451v1", "penrose_transform", "twistor_space", 0.9),
    ("2608.14451v1", "supersymmetry", "super_twistor_grassmannian", 0.8),
    ("2608.14451v1", "factorization", "four_point_correlator", 0.8),
    ("2608.14451v1", "half_fourier_transform", "spinor_helicity_variables", 0.8),

    # 7. 2608.14449v1 — Phase Space of Gravity on Null Hypersurfaces
    ("2608.14449v1", "carroll_boost", "gauge_freedom", 0.9),
    ("2608.14449v1", "ehresmann_connection", "background_structure", 0.8),
    ("2608.14449v1", "dirac_reduction", "poisson_bracket", 0.8),
    ("2608.14449v1", "shear_constraint", "spin2_bracket_nonlocality", 0.7),
    ("2608.14449v1", "null_transport_operator", "green_kernel", 0.8),

    # 8. 2608.14384v1 — Large lumps
    ("2608.14384v1", "kink_antikink_pair", "lump_solution", 0.9),
    ("2608.14384v1", "distance_parameter", "plateau_width", 0.8),
    ("2608.14384v1", "first_order_equation", "lump_potential", 0.9),
    ("2608.14384v1", "parent_kink", "lump_tails", 0.8),
    ("2608.14384v1", "lump_tails", "power_law_decay", 0.7),

    # 9. 2608.14410v1 — One-sided type-D Ricci-flat multi-centre metrics
    ("2608.14410v1", "tod_ansatz", "ricci_flat_metric", 0.8),
    ("2608.14410v1", "harmonic_function", "generating_potential", 0.9),
    ("2608.14410v1", "harmonic_conjugate", "generating_potential", 0.8),
    ("2608.14410v1", "inverse_scattering_method", "multi_soliton_solution", 0.8),
    ("2608.14410v1", "centre_count", "soliton_number", 0.6),

    # 10. 2608.14267v1 — gravitational scattering with massive scalar mediator
    ("2608.14267v1", "massive_scalar_mediator", "fourier_transform_complexity", 0.7),
    ("2608.14267v1", "scalar_force_range", "scattering_angle_resonance", 0.8),
    ("2608.14267v1", "scalar_cloud", "gravitational_mass_reduction", 0.8),
    ("2608.14267v1", "mediator_mass", "screening_effect", 0.7),
    ("2608.14267v1", "scalar_coupling", "post_minkowskian_expansion", 0.7),

    # 11. 2608.14259v1 — Compact-Support Wormholes (trace-coupled gravity)
    ("2608.14259v1", "trace_coupling", "wormhole_matter_reconstruction", 0.8),
    ("2608.14259v1", "anisotropic_source", "inversion_formula", 0.8),
    ("2608.14259v1", "matter_lagrangian_prescription", "reconstructed_matter", 0.7),
    ("2608.14259v1", "radial_nec_violation", "exoticity_localization", 0.8),
    ("2608.14259v1", "schwarzschild_deformation", "compact_core", 0.9),

    # 12. 2608.14204v1 — Asymptotic flatness beyond GR
    ("2608.14204v1", "asymptotic_symmetry_group", "balance_flux_equation", 0.8),
    ("2608.14204v1", "bondi_sachs_hierarchy", "falloff_condition", 0.8),
    ("2608.14204v1", "scalar_potential", "asymptotic_vacuum", 0.8),
    ("2608.14204v1", "stress_energy_tensor", "metric_decay", 0.7),
    ("2608.14204v1", "extra_degrees_of_freedom", "null_infinity", 0.7),

    # 13. 2608.14544v1 — GPU mixed quantum-classical Liouville MD
    ("2608.14544v1", "gpu_parallelization", "simulation_speedup", 0.9),
    ("2608.14544v1", "spawning_elimination", "thread_divergence_reduction", 0.8),
    ("2608.14544v1", "sampling_trajectory_count", "linear_scaling", 0.8),
    ("2608.14544v1", "momentum_jump_free_theory", "molecular_dynamics", 0.8),

    # 14. 2608.14508v1 — bulk DOS in non-Hermitian lattices
    ("2608.14508v1", "boundary_condition", "density_of_states", 0.8),
    ("2608.14508v1", "thermodynamic_limit", "universal_bulk_structure", 0.8),
    ("2608.14508v1", "point_gap_topology", "green_function_constraint", 0.7),
    ("2608.14508v1", "hermitization", "brown_measure", 0.8),
    ("2608.14508v1", "large_complex_frequency", "boundary_independence", 0.7),

    # 15. 2608.14493v1 — Measurement-Feedback Quantum Information Engine
    ("2608.14493v1", "measurement_feedback", "coherence_preparation", 0.8),
    ("2608.14493v1", "population_transfer", "conditional_work", 0.8),
    ("2608.14493v1", "coherence_transition", "interference_term", 0.8),
    ("2608.14493v1", "feedback_memory", "record_reset_cost", 0.7),
    ("2608.14493v1", "entropy_rate", "reversible_cost", 0.7),

    # 16. 2608.14476v1 — Universal Determinant for Continuum Fermions
    ("2608.14476v1", "slater_determinant", "fermionic_wavefunction", 0.8),
    ("2608.14476v1", "bosonic_wavefunction", "fermionic_approximation", 0.9),
    ("2608.14476v1", "antisymmetry", "determinant_count", 0.9),
    ("2608.14476v1", "coulomb_interaction", "sobolev_norm_requirement", 0.8),
    ("2608.14476v1", "local_energy_variance", "variational_monte_carlo", 0.7),

    # 17. 2608.14469v1 — Current fluctuations in non-additive open quantum system
    ("2608.14469v1", "lindblad_form", "markovian_dynamics", 0.8),
    ("2608.14469v1", "out_of_equilibrium_state", "net_current", 0.8),
    ("2608.14469v1", "non_additive_dissipator", "complete_positivity_breakdown", 0.8),
    ("2608.14469v1", "imperfect_jump_detection", "landauer_buttiker_current", 0.7),

    # 18. 2608.14468v1 — PT symmetry, noise-induced escape
    ("2608.14468v1", "gain_loss_balance", "long_lived_excitation", 0.8),
    ("2608.14468v1", "duffing_nonlinearity", "pt_phase_restriction", 0.8),
    ("2608.14468v1", "fluctuations", "first_passage_escape", 0.8),
    ("2608.14468v1", "two_photon_loss", "nonlinear_damping", 0.8),
    ("2608.14468v1", "nonlinear_damping", "stochastic_stability", 0.8),

    # 19. 2608.14447v1 — Angular displacement readout (GMR)
    ("2608.14447v1", "guided_mode_resonance", "angular_displacement_readout", 0.9),
    ("2608.14447v1", "narrow_linewidth", "displacement_imprecision", 0.8),
    ("2608.14447v1", "subwavelength_grating", "vibration_measurement", 0.8),
    ("2608.14447v1", "polarization_detuning", "transduction_signal", 0.7),
    ("2608.14447v1", "optical_power", "signal_to_noise_ratio", 0.7),

    # 20. 2608.14387v1 — Linearised quantum signal processing
    ("2608.14387v1", "uhet", "gqsp_linearisation", 0.8),
    ("2608.14387v1", "hamiltonian_dynamics", "singular_value_transformation", 0.8),
    ("2608.14387v1", "function_vanishing_at_origin", "efficient_transformation", 0.7),
    ("2608.14387v1", "black_box_dynamics", "singular_value_access", 0.8),

    # 21. 2608.14423v1 — X-rays heat the IGM (21-cm codes)
    ("2608.14423v1", "xray_heating", "igm_temperature", 0.9),
    ("2608.14423v1", "radiative_transfer_code", "power_spectrum_difference", 0.8),
    ("2608.14423v1", "1d_approximation", "temperature_distribution_discrepancy", 0.7),
    ("2608.14423v1", "igm_temperature", "21cm_signal", 0.8),
    ("2608.14423v1", "power_spectrum", "posterior_distribution", 0.7),

    # 22. 2608.14265v1 — Cosmicflows-4 large-scale motions
    ("2608.14265v1", "lcdm_prediction", "velocity_dipole", 0.8),
    ("2608.14265v1", "survey_window", "dipole_excess", 0.7),
    ("2608.14265v1", "peculiar_velocity", "coherent_flow", 0.8),
    ("2608.14265v1", "catalog_selection", "dipole_significance", 0.7),

    # 23. 2608.14183v1 — Cosmographic Reconstruction of Quintessence Potential
    ("2608.14183v1", "nonminimal_coupling", "potential_slope", 0.8),
    ("2608.14183v1", "cosmographic_parameters", "potential_reconstruction", 0.8),
    ("2608.14183v1", "planck_mass_running", "coupling_slope", 0.8),
    ("2608.14183v1", "gravitational_constant_variation", "observable_coefficient", 0.7),
    ("2608.14183v1", "scalar_kinetic_term_positivity", "effective_equation_of_state", 0.7),

    # 24. 2608.14170v1 — Primordial Power Asymmetry
    ("2608.14170v1", "primordial_power_asymmetry", "statistical_isotropy_departure", 0.8),
    ("2608.14170v1", "peculiar_velocity", "anisotropy_test", 0.7),
    ("2608.14170v1", "anisotropic_galaxy_bias", "quadrupolar_degeneracy", 0.8),
    ("2608.14170v1", "density_velocity_cross_spectrum", "degeneracy_breaking", 0.7),

    # 25. 2608.13692v1 — GW from Dimension-6 PQ phase transitions
    ("2608.13692v1", "dimension6_operator", "first_order_phase_transition", 0.8),
    ("2608.13692v1", "phase_transition", "gravitational_wave_signal", 0.8),
    ("2608.13692v1", "axion_model", "dark_matter_phenomenology", 0.7),
    ("2608.13692v1", "uv_completion", "phenomenological_signature", 0.6),

    # 26. 2608.13656v1 — Heavy Black Hole Seeds from Lyman-Werner radiation
    ("2608.13656v1", "lyman_werner_radiation", "gas_inflow_rate", 0.8),
    ("2608.13656v1", "gas_inflow_rate", "supermassive_star_formation", 0.8),
    ("2608.13656v1", "population_iii_star_mass", "black_hole_seed", 0.8),
    ("2608.13656v1", "halo_assembly_rate", "stellar_mass", 0.6),
    ("2608.13656v1", "radial_gas_infall", "protostellar_mass", 0.8),

    # 27. 2608.13650v1 — Axion Isocurvature Perturbations
    ("2608.13650v1", "inflationary_fluctuations", "domain_wall_network", 0.8),
    ("2608.13650v1", "domain_wall_collapse", "axion_energy_density", 0.8),
    ("2608.13650v1", "vacuum_energy_release", "superhorizon_correlation_transfer", 0.7),
    ("2608.13650v1", "domain_wall_annihilation", "isocurvature_perturbation", 0.8),

    # 28. 2608.13648v1 — BBH merger rate comparison
    ("2608.13648v1", "population_synthesis_model", "bbh_merger_rate", 0.8),
    ("2608.13648v1", "metallicity_distribution", "merger_rate_tension", 0.8),
    ("2608.13648v1", "low_metallicity_tail", "merger_rate_overprediction", 0.7),
    ("2608.13648v1", "iron_abundance", "metallicity_distribution", 0.7),
]


def main():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    fq = FeedQueue(data_dir)

    # 去重 (同一 paper 内同一对)
    seen = set()
    papers = {}
    total = 0

    for arxiv_id, src, dst, conf in EDGES:
        if src == dst:
            continue
        key = (arxiv_id, src, dst)
        if key in seen:
            continue
        seen.add(key)
        fq.feed_edge(
            src=src,
            dst=dst,
            law=f"arxiv:{arxiv_id}",
            source=f"arxiv:{arxiv_id}",
            domain="physics_research",
            initial_s=round(conf * 0.2, 3),
        )
        papers.setdefault(arxiv_id, 0)
        papers[arxiv_id] += 1
        total += 1

    print(f"[FEED] wrote {total} edges across {len(papers)} papers")
    for pid in sorted(papers):
        print(f"  {pid}: {papers[pid]} edges")

    # 更新 fed state, 避免 cron_feed_arxiv.py 重复喂同一批
    fed_path = os.path.join(data_dir, ".arxiv_fed_state.json")
    fed_ids = set()
    if os.path.exists(fed_path):
        try:
            with open(fed_path) as f:
                fed_ids = set(json.load(f))
        except Exception:
            fed_ids = set()
    fed_ids.update(papers.keys())
    with open(fed_path, "w") as f:
        json.dump(sorted(fed_ids), f)

    # 验证 feed_queue
    qp = os.path.join(data_dir, "feed_queue.jsonl")
    if os.path.exists(qp):
        with open(qp) as f:
            n = sum(1 for _ in f)
        print(f"[FEED] feed_queue.jsonl total lines now: {n}")


if __name__ == "__main__":
    main()
