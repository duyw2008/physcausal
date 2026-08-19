#!/usr/bin/env python3
"""Cron: inject physics causal edges extracted from 26 new arXiv papers into feed_queue.jsonl."""
import json, os, time

DATA = "/home/duyw/physcausal/data"
QUEUE = os.path.join(DATA, "feed_queue.jsonl")
FED_STATE = os.path.join(DATA, ".arxiv_fed_state.json")

# arxiv_id -> [(src, dst, confidence), ...]
EDGES = {
    "2608.13498v1": [
        ("scalar_perturbations", "effective_energy_momentum_tensor", 0.9),
        ("gauge_condition", "bardeen_potential", 0.85),
        ("slow_roll_parameter", "ultraviolet_2emt_enhancement", 0.85),
        ("gradient_term", "uniform_density_2emt_enhancement", 0.8),
        ("wavelength_regime", "gauge_dependence_structure", 0.7),
        ("adiabatic_super_hubble_mode", "gauge_slicing_coincidence", 0.75),
    ],
    "2608.13488v1": [
        ("lambda", "equation_of_state_deviation", 0.9),
        ("lambda", "density_parameter_correction", 0.85),
        ("background_expansion_correction", "eos_redshift_dependence", 0.8),
        ("expansion_order", "approximation_accuracy", 0.85),
        ("exponential_potential", "thawing_dark_energy_dynamics", 0.7),
    ],
    "2608.13475v1": [
        ("unfolded_spectrum", "oscillator_deformation", 0.85),
        ("oscillator_deformation", "matrix_elements", 0.9),
        ("matrix_elements", "distance_shells", 0.85),
        ("beta_parameter", "distance_shell_moments", 0.8),
        ("distance_shell_moments", "universality_class", 0.85),
        ("inverse_spectral_reconstruction", "gue_character_zeta_zeros", 0.75),
    ],
    "2608.13462v1": [
        ("aperiodicity", "return_probability_decay", 0.8),
        ("aperiodicity", "hilbert_space_ergodic_exploration", 0.75),
        ("return_probability_decay", "macroscopic_observable_equilibration", 0.9),
        ("effective_dimension", "infinite_time_equilibration", 0.8),
        ("aperiodicity", "finite_time_thermalization", 0.85),
    ],
    "2608.13449v1": [
        ("spectral_density_localization", "harvestable_entanglement", 0.9),
        ("quality_factor", "maximum_concurrence", 0.85),
        ("cavity_linewidth", "maximum_concurrence", 0.8),
        ("qubit_cavity_detuning", "quality_factor", 0.8),
        ("inverse_participation_ratio", "maximum_concurrence", 0.7),
    ],
    "2608.13557v1": [
        ("speed_of_sound", "maximum_supercooling", 0.9),
        ("spacetime_dimension", "supercooling_suppression", 0.85),
        ("minimal_temperature", "supercooling_magnitude", 0.85),
        ("horizon_localization", "black_brane_analytic_solution", 0.75),
        ("scalar_potential_form", "confinement_transition_universality", 0.65),
    ],
    "2608.13542v1": [
        ("slow_degrees_of_freedom", "quasi_conserved_observable_dynamics", 0.85),
        ("fast_relaxation_timescale", "systematic_expansion", 0.8),
        ("kinetic_theory", "israel_stewart_dynamics", 0.85),
        ("microscopic_symmetry_constraints", "higher_order_corrections", 0.75),
        ("quasi_conservation", "transient_hydrodynamic_universality_class", 0.7),
    ],
    "2608.13529v1": [
        ("self_accelerating_branch", "kinetic_coefficient_vanishing", 0.85),
        ("kinetic_coefficient_vanishing", "vector_mode_strong_coupling", 0.85),
        ("minimal_matter", "vector_kinetic_coefficient", 0.7),
        ("friedmann_equation", "shift_constraint_cancellation", 0.7),
        ("branch_choice", "vector_sector_health", 0.75),
    ],
    "2608.13378v1": [
        ("thermal_fluctuations", "entropy_corrections", 0.85),
        ("entropy_corrections", "thermodynamic_potential_modification", 0.8),
        ("thermal_fluctuations", "specific_heat_divergence", 0.85),
        ("specific_heat_sign_change", "second_order_phase_transition", 0.85),
        ("quantum_corrections", "black_hole_stability", 0.8),
    ],
    "2608.13319v1": [
        ("boundary_metric", "renormalized_generating_functional", 0.85),
        ("scalar_source", "boundary_response", 0.8),
        ("string_coupling_data", "holographic_observable", 0.85),
        ("curvature_anomaly_sum", "gauss_bonnet_coefficient", 0.75),
        ("radial_hierarchy", "ward_identities", 0.7),
    ],
    "2608.13289v1": [
        ("curvature_dependent_transform", "differential_obstruction", 0.85),
        ("auxiliary_scalar", "forward_map_localization", 0.8),
        ("differential_constraint", "metric_variable_recovery", 0.8),
        ("fr_gravity", "parent_scalar_tensor_theory", 0.75),
        ("nonpolynomial_projector", "finite_jet_inverse_absence", 0.75),
    ],
    "2608.13282v1": [
        ("bumblebee_vev", "cosmic_expansion", 0.85),
        ("bumblebee_vev", "gravitational_wave_amplitude", 0.85),
        ("supernova_data", "background_parameter_constraint", 0.85),
        ("gravitational_wave_sector", "lorentz_violation_evolution_index", 0.8),
        ("standard_sirens", "luminosity_distance_measurement", 0.9),
    ],
    "2608.13561v1": [
        ("indefinite_causal_order", "eavesdropper_detection", 0.85),
        ("quantum_switch", "key_material_conservation", 0.8),
        ("control_qubit_measurement", "eavesdropper_detection", 0.85),
        ("post_selection_requirement", "security_limitation", 0.75),
        ("polarization_measurement_technique", "path_coherence_preservation", 0.7),
    ],
    "2608.13551v1": [
        ("ppt_property", "finite_entanglement_breaking_index", 0.9),
        ("low_entanglement_dimensionality", "entanglement_breaking_index_bound", 0.8),
        ("entanglement_breaking_index_bound", "ppt_cubed_conjecture_support", 0.7),
    ],
    "2608.13543v1": [
        ("network_topology", "nonlocal_operation_count", 0.8),
        ("gaussian_elimination", "cnot_circuit_synthesis", 0.85),
        ("css_code_encoding", "inter_block_transversal_cnot", 0.75),
        ("pauli_exponential_representation", "clifford_rz_synthesis", 0.8),
        ("distributed_architecture", "nonlocal_operation_minimization", 0.7),
    ],
    "2608.13533v1": [
        ("memory_kernel", "non_markovian_dynamics", 0.9),
        ("memory_strength", "algorithm_efficiency", 0.8),
        ("exponential_kernel_decomposition", "markovianization", 0.8),
        ("markovianization", "efficient_quantum_simulation", 0.8),
        ("volterra_equation", "quantum_state_encoding", 0.85),
    ],
    "2608.13530v1": [
        ("inductive_shunt", "relaxation_time", 0.85),
        ("potential_well_separation", "wavefunction_overlap_reduction", 0.85),
        ("wavefunction_overlap_reduction", "decoherence_suppression", 0.8),
        ("inductive_shunt", "fluxonium_regime", 0.75),
        ("spin_degree_of_freedom", "superconducting_qubit_advantage", 0.7),
    ],
    "2608.13528v1": [
        ("circuit_depth", "group_design_formation", 0.9),
        ("sublinear_depth", "design_impossibility", 0.85),
        ("ambient_unitaries", "design_formation_enablement", 0.7),
        ("circuit_depth", "tomography_overhead", 0.75),
    ],
    "2608.13521v1": [
        ("single_qubit_coupling", "measurement_count_reduction", 0.9),
        ("quantum_feature_sensing", "fourier_coefficient_learning", 0.85),
        ("quantum_phase_space_inference", "optimal_learning_algorithm", 0.85),
        ("quantum_advantage", "weak_signal_dark_matter_detection", 0.8),
        ("control_qubit", "classical_signal_learning", 0.85),
    ],
    "2608.13493v1": [
        ("gravitational_coupling", "collective_coherence", 0.85),
        ("gravitational_coupling", "inter_particle_correlation", 0.85),
        ("temperature", "coherence_redistribution", 0.8),
        ("thermal_fluctuations", "localized_coherence_robustness", 0.75),
        ("double_well_confinement", "gravitational_cat_state", 0.7),
    ],
    "2608.13347v1": [
        ("excursion_set_theory", "outer_density_profile", 0.85),
        ("window_function", "density_trajectory_correlation", 0.85),
        ("simplifying_assumptions", "analytic_profile_systematic_error", 0.8),
        ("turnaround_radius", "density_profile_deviation_point", 0.7),
    ],
    "2608.13346v1": [
        ("scalar_field_mass", "fast_oscillation", 0.85),
        ("oscillation_onset_detection", "numerical_tractability", 0.8),
        ("averaging_technique", "oscillation_absorption", 0.85),
        ("hubble_parameter", "oscillation_regime", 0.8),
        ("averaging_technique", "cosmological_constraint_update", 0.7),
    ],
    "2608.13257v1": [
        ("fourier_transform_spectrometer", "cmb_spectral_distortion_sensitivity", 0.85),
        ("ray_tracing_simulation", "optical_configuration", 0.8),
        ("frequency_band_split", "focal_plane_assignment", 0.75),
        ("bolometric_detector", "spectral_measurement", 0.7),
    ],
    "2608.13225v1": [
        ("breadboard_characterization", "systematic_effect_identification", 0.8),
        ("dichroic", "frequency_sub_band_split", 0.85),
        ("ray_tracing_simulation", "optical_configuration", 0.8),
        ("feed_horn_coupling", "detector_illumination", 0.7),
    ],
    "2608.13206v1": [
        ("superhorizon_curvature_perturbation", "primordial_black_hole_formation", 0.9),
        ("scaled_gamma_driver", "cosmic_timestep_growth", 0.85),
        ("curvature_perturbation_amplitude", "collapse_threshold", 0.8),
        ("pbh_mass", "zeldovich_novikov_accretion", 0.8),
        ("near_critical_collapse", "critical_exponent", 0.8),
    ],
    "2608.13185v1": [
        ("passive_cooling_chain", "instrument_temperature", 0.85),
        ("adiabatic_demagnetisation_refrigerator", "sub_kelvin_temperature", 0.85),
        ("v_groove_radiator", "staged_cooling", 0.8),
        ("thermal_isolation", "focal_plane_temperature", 0.75),
        ("cryocooler", "shield_cooling", 0.8),
    ],
}

def main():
    total_edges = 0
    papers_fed = 0
    with open(QUEUE, "a") as f:
        for arxiv_id, edges in EDGES.items():
            n = 0
            for src, dst, conf in edges:
                item = {
                    "source": "arxiv_feed",
                    "type": "edge",
                    "data": {
                        "src": src,
                        "dst": dst,
                        "law": f"arxiv:{arxiv_id}",
                        "domain": "physics_research",
                        "initial_s": round(conf * 0.2, 3),
                    },
                    "ts": time.time(),
                }
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                n += 1
            total_edges += n
            papers_fed += 1
            print(f"  [{arxiv_id}] -> {n} edges")

    # mark fed
    fed = set()
    if os.path.exists(FED_STATE):
        with open(FED_STATE) as f:
            fed = set(json.load(f))
    fed.update(EDGES.keys())
    with open(FED_STATE, "w") as f:
        json.dump(sorted(fed), f)

    print(f"\n[DONE] {papers_fed} papers -> {total_edges} causal edges into feed_queue.jsonl")
    print(f"[FED-STATE] total fed ids now: {len(fed)}")

if __name__ == "__main__":
    main()
