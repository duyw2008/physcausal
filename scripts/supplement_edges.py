#!/usr/bin/env python3
"""Generate supplementary causal edges for sparse arxiv papers from title analysis."""
import json, time, os, sys

data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

# Load sparse papers
papers = []
with open(os.path.join(data_dir, 'arxiv_reading_list.jsonl')) as f:
    for line in f:
        line = line.strip()
        if line:
            papers.append(json.loads(line))

pending = [p for p in papers if not p.get('promoted', False)]
sparse = {p['arxiv_id']: p for p in pending if len(p.get('concepts', [])) < 3}

# Supplementary edges inferred from titles by LLM physics reasoning
# Format: arxiv_id -> [(src, dst, confidence)]
supplementary = {
    # 0: "On the strong coupling limit of Yang-Mills matrix models"
    "2607.21593v1": [
        ("strong_coupling_regime", "matrix_model_reduction", 0.75),
        ("yang_mills_action", "eigenvalue_dynamics", 0.65),
        ("coupling_constant", "emergent_geometry", 0.6),
    ],
    # 1: "A geometric framework for spin relaxation"
    "2607.21569v1": [
        ("geometric_phase", "spin_relaxation_rate", 0.8),
        ("curvature_of_state_space", "decoherence_time", 0.7),
    ],
    # 2: "Sharp Bounds on Ground State Energy of the SYK Model"
    "2607.27185v1": [
        ("disorder_averaging", "ground_state_energy_bound", 0.85),
        ("fermion_number_N", "energy_spectrum_edge", 0.7),
        ("random_coupling_tensor", "many_body_localization", 0.6),
        ("syk_non_fermi_liquid", "energy_variance", 0.55),
    ],
    # 3: "Explicit Matrices over Z2 with CNOT and Row Complexity..."
    "2607.28598v1": [
        ("cnot_count", "circuit_complexity", 0.8),
        ("linear_reversible_circuits", "row_complexity_bound", 0.7),
        ("z2_linear_algebra", "gate_synthesis", 0.6),
    ],
    # 4: "Subleading Asymptotic Charges in Massless Scalar QED"
    "2608.02368v1": [
        ("soft_photon_theorem", "subleading_asymptotic_charge", 0.8),
        ("gauge_symmetry", "memory_effect", 0.7),
        ("scalar_field_coupling", "infrared_divergence", 0.6),
    ],
    # 5: "Superloop Equations and Minimal Surfaces I: Confining minimal surface in 4D, N=1 SYM"
    "2608.02262v1": [
        ("wilson_loop", "minimal_surface_area", 0.85),
        ("superloop_equation", "confinement_potential", 0.75),
        ("n1_supersymmetry", "ads_cft_correspondence", 0.65),
    ],
    # 6: "Gauge and Metaphysics of Spacetime"
    "2608.02542v1": [
        ("gauge_symmetry", "spacetime_ontology", 0.7),
        ("local_symmetry", "empirical_underdetermination", 0.65),
        ("fiber_bundle_formalism", "substantivalism", 0.55),
    ],
    # 7: "Optimal Quantum de Finetti Theorems via Argmax Rounding"
    "2608.02590v1": [
        ("quantum_de_finetti_theorem", "permutation_invariance", 0.8),
        ("argmax_rounding", "approximation_error_bound", 0.7),
    ],
    # 8: "Entanglement of flower states"
    "2608.02587v1": [
        ("flower_state_geometry", "entanglement_entropy", 0.8),
        ("graph_state_structure", "multipartite_entanglement", 0.7),
        ("petal_configuration", "entanglement_persistency", 0.6),
    ],
    # 9: "High-dimensional quantum process tomography with undetected photons"
    "2608.02490v1": [
        ("undetected_photons", "process_tomography_fidelity", 0.75),
        ("induced_coherence", "quantum_channel_reconstruction", 0.7),
    ],
    # 10: "Effective reheating in Gauss-Bonnet inflation with μ(φ,X) coupling"
    "2608.02506v1": [
        ("gauss_bonnet_coupling", "reheating_temperature", 0.8),
        ("kinetic_coupling_mu", "inflaton_decay_rate", 0.7),
        ("non_minimal_gravity", "primordial_perturbations", 0.6),
    ],
    # 11: "Testing Scale-Dependent Suppression of Structure Growth in the Linear Regime"
    "2608.02175v1": [
        ("scale_dependent_growth", "matter_power_spectrum", 0.8),
        ("modified_gravity", "linear_growth_rate_fsigma8", 0.7),
    ],
    # 12: "Weak local law and delocalization for the Sachdev-Ye-Kitaev model"
    "2608.03771v1": [
        ("weak_local_law", "eigenstate_delocalization", 0.8),
        ("random_matrix_ensemble", "level_spacing_statistics", 0.7),
    ],
    # 13: "Logarithmic Soft Photon Theorem and Waveform Tails in Higher Dimensions"
    "2608.03747v1": [
        ("logarithmic_soft_theorem", "waveform_tail_behavior", 0.8),
        ("spacetime_dimension", "radiation_falloff", 0.7),
    ],
    # 14: "Two-loop QCD amplitudes for ttW production at the LHC..."
    "2608.03746v1": [
        ("leading_colour_approximation", "two_loop_amplitude", 0.8),
        ("top_quark_pair_production", "w_boson_associated_production", 0.75),
    ],
    # 15: "Integrated cosmological memory: A dark-siren method to probe dark energy"
    "2608.03739v1": [
        ("gravitational_wave_memory", "cosmological_distance", 0.8),
        ("dark_siren_events", "hubble_constant_measurement", 0.75),
        ("integrated_memory_effect", "dark_energy_equation_of_state", 0.65),
    ],
    # 16: "Charged topological geons with a self-gravitating scalar field"
    "2608.03942v1": [
        ("self_gravitating_scalar", "topological_geon_stability", 0.8),
        ("electric_charge", "gravitational_soliton", 0.7),
    ],
    # 17: "A lower bound on the classical simulation cost of star-network correlations"
    "2608.03986v1": [
        ("star_network_topology", "classical_simulation_cost", 0.85),
        ("quantum_correlation", "simulation_complexity_lower_bound", 0.75),
    ],
    # 18: "A quantum game of telephone"
    "2608.03963v1": [
        ("quantum_communication_channel", "information_degradation", 0.75),
        ("sequential_measurement", "quantum_advantage_in_games", 0.7),
    ],
    # 19: "Separating quantum circuits from classical LLMs"
    "2608.03962v1": [
        ("quantum_circuit_expressivity", "classical_llm_simulation", 0.8),
        ("quantum_supremacy_task", "transformer_model_capability", 0.7),
    ],
    # 20: "Exact Tradeoff Between Quantum Error Correction and Quantum Darwinism..."
    "2608.03944v1": [
        ("quantum_error_correction_code", "quantum_darwinism_redundancy", 0.85),
        ("information_theoretic_bound", "objectivity_of_observables", 0.75),
    ],
    # 21: "Fisher Forecasting for the DESC with Augur"
    "2608.03876v1": [
        ("fisher_matrix_formalism", "cosmological_parameter_constraints", 0.85),
        ("dark_energy_survey", "forecast_pipeline_augur", 0.7),
        ("survey_design", "parameter_uncertainty", 0.6),
    ],
    # 22: "From One to Eight: Supersymmetry Restoration in Lattice 3D N=4 SYM"
    "2608.05099v1": [
        ("lattice_regularization", "supersymmetry_restoration", 0.85),
        ("continuum_limit", "n4_supercharge_preservation", 0.75),
    ],
    # 23: "Generalized comodule tube algebras for boundary and domain wall defects of (2+1)D topological order"
    "2608.05071v1": [
        ("tube_algebra", "topological_boundary_defect", 0.8),
        ("comodule_structure", "domain_wall_fusion", 0.75),
        ("modular_tensor_category", "anyon_condensation", 0.65),
    ],
    # 24: "Correlation-based Modeling of Seismic Newtonian Noise..."
    "2608.05117v1": [
        ("seismic_wavefield", "newtonian_gravity_noise", 0.85),
        ("correlation_function", "gravitational_detector_sensitivity", 0.7),
        ("half_space_medium", "noise_power_spectrum", 0.6),
    ],
    # 25: "Ambiguity in matter sector for modified gravity involving δ²Lm/δgδg..."
    "2608.04867v1": [
        ("matter_lagrangian_variation", "modified_gravity_field_equations", 0.85),
        ("degeneracy_condition", "astrophysical_implications", 0.7),
    ],
    # 26: "Representational separation between unitary and channel quantum generative models..."
    "2608.05110v1": [
        ("shared_classical_randomness", "quantum_generative_expressivity", 0.8),
        ("unitary_vs_channel_model", "representational_power_gap", 0.75),
    ],
    # 27: "Imaginarity as a necessary resource for trainability in QAOA"
    "2608.05093v1": [
        ("imaginarity_resource", "qaoa_trainability", 0.85),
        ("barren_plateau_avoidance", "complex_phase_parameters", 0.7),
        ("variational_circuit", "gradient_variance", 0.6),
    ],
    # 28: "Perfect Games in Dimension-Bounded Communication"
    "2608.05092v1": [
        ("dimension_bounded_communication", "perfect_game_strategy", 0.8),
        ("quantum_vs_classical_communication", "entanglement_assisted_game", 0.7),
    ],
    # 29: "Constructing Non-Hermitian Theories with Tunable Exceptional Points..."
    "2608.05052v1": [
        ("non_hermitian_hamiltonian", "exceptional_point_tunability", 0.85),
        ("pt_symmetry_breaking", "state_purification_rate", 0.75),
    ],
    # 30: "The Quantum Mechanics of Rare Events: From Quantum Walks to Stochastic Inflation"
    "2608.06319v1": [
        ("quantum_walk", "rare_event_statistics", 0.8),
        ("stochastic_inflation", "tail_distribution", 0.7),
        ("large_deviation_theory", "quantum_tunneling_rate", 0.65),
    ],
    # 31: "Quantum Lifts of Noninteger Power Law Field Theories"
    "2608.06282v1": [
        ("noninteger_scaling_dimension", "quantum_field_theory_lift", 0.8),
        ("conformal_field_theory", "fractional_power_interaction", 0.7),
    ],
    # 32: "Approximate Quantum Error Correction at Chiral Topological Edges"
    "2608.06258v1": [
        ("chiral_edge_mode", "approximate_error_correction", 0.85),
        ("topological_order", "boundary_code_protection", 0.75),
    ],
    # 33: "Isomorphic Emergence of Lorentz and Gauge Symmetries..."
    "2608.06244v1": [
        ("continuum_mechanics_formalism", "lorentz_symmetry_emergence", 0.8),
        ("isomorphic_mapping", "gauge_symmetry_generation", 0.75),
        ("elastic_medium", "effective_field_theory", 0.65),
    ],
    # 34: "A Neutron Star Hidden Inside a Black Hole"
    "2608.06224v1": [
        ("neutron_star_configuration", "black_hole_interior", 0.75),
        ("tolman_oppenheimer_volkoff_equation", "gravitational_collapse", 0.7),
        ("compact_object_twin", "event_horizon_interior", 0.6),
    ],
    # 35: "Quasinormal Modes of Gauss-Bonnet Black Holes via the Spectral Method..."
    "2608.06083v1": [
        ("gauss_bonnet_coupling", "quasinormal_mode_spectrum", 0.85),
        ("spectral_method", "black_hole_perturbation_decay", 0.75),
    ],
    # 36: "Radial spectra and dynamical signatures of excited boson stars"
    "2608.06067v1": [
        ("boson_star_excitation", "radial_oscillation_spectrum", 0.85),
        ("scalar_field_self_interaction", "dynamical_stability", 0.75),
    ],
    # 37: "Scalar Hair at the String-Black-Hole Correspondence"
    "2608.06016v1": [
        ("string_black_hole_correspondence", "scalar_hair_configuration", 0.8),
        ("alpha_prime_correction", "no_hair_theorem_violation", 0.7),
    ],
    # 38: "Dimension-Free Polylogarithmic Quantum Shadow Tomography from Sequential Pretty-Good Measurements"
    "2608.06345v1": [
        ("pretty_good_measurement", "shadow_tomography_sample_complexity", 0.85),
        ("sequential_measurement_scheme", "dimension_free_bound", 0.75),
    ],
    # 39: "Multi-State Geometry of Density Matrices and Rectification Sum Rules"
    "2608.06326v1": [
        ("density_matrix_geometry", "rectification_sum_rule", 0.8),
        ("multi_state_manifold", "quantum_transport_asymmetry", 0.7),
        ("bures_metric", "current_rectification", 0.6),
    ],
    # 40: "Breaking Memory Bottlenecks in Quantum Control Systems..."
    "2608.06318v1": [
        ("quantum_control_memory", "experimental_throughput", 0.8),
        ("waveform_streaming", "control_precision", 0.7),
        ("real_time_feedback", "qubit_gate_fidelity", 0.6),
    ],
    # 41: "On Optimal Quantum Data Hiding and Maximal Separable Ball"
    "2608.06308v1": [
        ("quantum_data_hiding", "separable_ball_radius", 0.85),
        ("entanglement_witness", "information_concealment_capacity", 0.7),
    ],
    # 42: "Reanalyzing Megamasers: a low value of H0 from a local probe..."
    "2608.06247v1": [
        ("megamaser_distance_ladder", "hubble_constant_h0", 0.85),
        ("local_probe", "hubble_tension_resolution", 0.75),
    ],
    # 43: "Optical Counterparts of MeerKLASS L-band and UHF-band surveys"
    "2608.05923v1": [
        ("radio_survey_catalog", "optical_counterpart_crossmatch", 0.8),
        ("meerklass_survey", "galaxy_redshift_distribution", 0.7),
        ("l_band_vs_uhf", "source_classification", 0.6),
    ],
}

# Now append these as edge-type feeds to feed_queue.jsonl
queue_path = os.path.join(data_dir, 'feed_queue.jsonl')
new_edges = 0

with open(queue_path, 'a') as fq:
    for arxiv_id, edges in supplementary.items():
        # Check if the paper exists in sparse
        if arxiv_id not in sparse:
            print(f"  WARNING: {arxiv_id} not found in sparse list, skipping")
            continue
        for src, dst, conf in edges:
            item = {
                "source": f"arxiv:{arxiv_id}",
                "type": "edge",
                "data": {
                    "src": src,
                    "dst": dst,
                    "law": "arxiv_title_inference",
                    "domain": "research",
                    "initial_s": round(0.05 * conf, 4)
                },
                "ts": time.time()
            }
            fq.write(json.dumps(item, ensure_ascii=False) + '\n')
            new_edges += 1

print(f"Added {new_edges} supplementary edges from title inference")

# Summary stats
total_new = sum(len(v) for v in supplementary.values())
unchanged = len(sparse) - len(supplementary)
print(f"Enriched {len(supplementary)}/{len(sparse)} sparse papers with {total_new} additional edges")
if unchanged:
    print(f"{unchanged} papers unchanged (no supplementary edges extracted)")
