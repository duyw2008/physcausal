#!/usr/bin/env python3
"""Cron job: extract causal edges from arXiv abstracts and feed to queue."""
import json, time, os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(data_dir, exist_ok=True)
queue_path = os.path.join(data_dir, 'feed_queue.jsonl')

edges = [
    # 2607.28543 - Soft charges and zero modes at null boundaries
    ('zero_mode', 'canonical_structure', 'zero_mode->canonical_structure', 'hep-th'),
    ('asymptotic_symmetry', 'conserved_charge', 'asymptotic_symmetry->conserved_charge', 'hep-th'),
    ('zero_mode', 'quasilocal_edge_observable', 'zero_mode->edge_observable', 'hep-th'),
    ('null_boundary', 'zero_mode_ambiguity', 'null_boundary->zero_mode_ambiguity', 'hep-th'),

    # 2607.28518 - Redundant moments of non-melonic random tensor models
    ('large_N_limit', 'redundant_moments', 'large_N->redundant_moments', 'hep-th'),
    ('melonic_operator_degree', 'expectation_value', 'operator_degree->expectation', 'hep-th'),
    ('redundant_moments', 'tensor_bootstrap_simplification', 'redundancy->bootstrap_simplify', 'hep-th'),

    # 2607.28502 - Beyond monomial alpha-attractors
    ('quartic_coefficient', 'scalar_spectral_index', 'quartic_coeff->ns', 'astro-ph.CO'),
    ('binomial_potential', 'non_universal_ns', 'binomial_pot->non_universal_ns', 'astro-ph.CO'),
    ('quartic_dominated_reheating', 'time_dependent_eos', 'quartic_reheat->td_eos', 'astro-ph.CO'),
    ('potential_form', 'reheating_equation_of_state', 'potential_form->w_reheat', 'astro-ph.CO'),

    # 2607.28486 - Hayden-Preskill recovery at finite temperature
    ('temperature', 'postselection_probability', 'T->postselection_prob', 'hep-th'),
    ('swap_gate', 'scrambler_initial_state_relation', 'SWAP->scrambler_initial_relation', 'hep-th'),
    ('scrambling_strength', 'conditional_fidelity', 'scramble->fidelity', 'hep-th'),
    ('operator_spreading', 'information_recovery', 'operator_spread->info_recovery', 'hep-th'),

    # 2607.28445 - Inflation, Open Universes, and Dark Energy
    ('spatial_curvature', 'scalar_spectral_index', 'Omega_k->ns', 'astro-ph.CO'),
    ('dark_energy_eos', 'scalar_spectral_index', 'w0_wa->ns', 'astro-ph.CO'),
    ('negative_spatial_curvature', 'starobinsky_tension_reduction', 'neg_curv->tension_reduce', 'astro-ph.CO'),
    ('dynamical_dark_energy', 'spectral_index_reduction', 'dyn_DE->ns_down', 'astro-ph.CO'),

    # 2607.28622 - 4D Model-agnostic Probe into BBH Subpopulations
    ('evolutionary_channel', 'bbh_subpopulation', 'channel->subpop', 'astro-ph.HE'),
    ('primary_mass', 'spin_parameter_correlation', 'mass->spin_corr', 'astro-ph.HE'),
    ('mass_range', 'subpopulation_origin', 'mass_range->origin', 'astro-ph.HE'),
    ('data_dimensionality', 'astrophysical_constraint', 'dim->constraint', 'astro-ph.HE'),

    # 2607.28592 - LISA Reconstruction Landscape for Metastable Cosmic Strings
    ('string_network_lifetime', 'gw_spectrum_infrared_tail', 'lifetime->IR_tail', 'astro-ph.CO'),
    ('monopole_pair_nucleation', 'string_network_decay', 'monopole_nucl->decay', 'astro-ph.CO'),
    ('string_tension', 'LISA_detectability', 'tension->detectability', 'astro-ph.CO'),
    ('spectral_features', 'parameter_reconstruction', 'spectral_features->reconstruction', 'astro-ph.CO'),

    # 2607.28539 - Search for GW + high-energy neutrinos
    ('high_energy_neutrino', 'gravitational_wave_transient', 'HE_nu->GW_transient', 'astro-ph.HE'),
    ('gw_signal_strength', 'source_distance_lower_bound', 'gw_strength->distance_bound', 'astro-ph.HE'),
    ('targeted_unmodeled_search', 'weak_signal_sensitivity', 'unmodeled_search->sensitivity', 'astro-ph.HE'),

    # 2607.28454 - Integrability in Asymptotic Symmetries: BMS3
    ('polynomial_symbols', 'bms3_bihamiltonian_structure', 'poly_symb->biHamiltonian', 'gr-qc'),
    ('nijenhuis_operator', 'integrable_hierarchy', 'Nijenhuis->integrability', 'gr-qc'),
    ('ads3_structure', 'flat_space_limit', 'AdS3->flat_limit', 'gr-qc'),

    # 2607.28448 - Dynamics of compact binaries in massive sGB
    ('scalar_field_mass', 'binding_energy_correction', 'scalar_mass->binding_E', 'gr-qc'),
    ('mass_ratio', 'scalar_mass_effect_magnitude', 'mass_ratio->effect_size', 'gr-qc'),
    ('eccentricity', 'scalar_mass_effect_magnitude', 'ecc->effect_size', 'gr-qc'),
    ('higher_curvature_correction', 'scalar_condensate', 'curvature->condensate', 'gr-qc'),

    # 2607.28621 - Lifting Lifted Product Codes
    ('group_extension', 'code_size', 'group_ext->code_size', 'quant-ph'),
    ('graph_lift', 'tanner_graph_local_structure', 'graph_lift->tanner_local', 'quant-ph'),
    ('chain_map', 'code_parameters', 'chain_map->params', 'quant-ph'),
    ('lifting_construction', 'thermodynamic_family', 'lifting->thermo_family', 'quant-ph'),

    # 2607.28610 - Learning Arbitrary Lindbladians
    ('time_evolution', 'lindbladian_coefficients', 'time_evo->Lindblad_coeffs', 'quant-ph'),
    ('dynamical_strength_Lambda', 'experiment_count', 'Lambda->exp_count', 'quant-ph'),
    ('product_pauli_eigenstate', 'support_learning', 'Pauli_prep->support', 'quant-ph'),
    ('random_stabilizer_state', 'coefficient_estimation', 'stab_state->coeff_est', 'quant-ph'),

    # 2607.28605 - Logical computation with canonical lifted product codes
    ('physical_qubit_overhead', 'logical_qubit_count', 'phys_overhead->log_count', 'quant-ph'),
    ('cyclic_symmetry', 'canonical_logical_basis', 'cyclic_sym->canonical_basis', 'quant-ph'),
    ('code_surgery_gadget_count', 'logical_operation_completeness', 'gadget_count->op_complete', 'quant-ph'),
    ('code_structure', 'fault_tolerant_computation_efficiency', 'code_struct->FT_efficiency', 'quant-ph'),

    # 2607.28602 - Pauli Encodings & Unclonable Encryption
    ('number_of_pauli_strings', 'monogamy_winning_probability', 'K->win_prob', 'quant-ph'),
    ('pauli_string_structure', 'unclonable_security', 'Pauli_struct->security', 'quant-ph'),
    ('pairwise_anticommutation', 'sdp_bound', 'anticommute->SDP_bound', 'quant-ph'),

    # 2607.28600 - SymFT: Fault-Tolerant Quantum Circuit Simulation
    ('clifford_circuit', 'branch_probability_sampling', 'Clifford->branch_prob', 'quant-ph'),
    ('stabilizer_subcircuit', 'sampling_performance', 'stabilizer->perf', 'quant-ph'),
    ('non_clifford_operation', 'exact_sampling_cost', 'nonClifford->cost', 'quant-ph'),
    ('adaptive_stabilizer_coordinate', 'sampling_throughput', 'adapt_coord->throughput', 'quant-ph'),

    # 2607.28598 - Explicit Matrices over Z2 with CNOT
    ('matrix_size', 'cnot_complexity', 'n->CNOT_complexity', 'quant-ph'),
    ('local_logic_gate', 'row_reduction_complexity', 'local_gate->row_complexity', 'quant-ph'),
    ('permutation_group', 'affine_transformation', 'perm_group->affine_transform', 'quant-ph'),

    # 2607.28579 - Quantum Chaos and Diffusive Transport
    ('geometric_randomness', 'chaotic_dynamics', 'geo_random->chaos', 'quant-ph'),
    ('layer_size', 'level_repulsion', 'layer_size->level_rep', 'quant-ph'),
    ('graph_dimensionality', 'diffusive_transport', 'graph_dim->diffusion', 'quant-ph'),
    ('quasi_1d_limit', 'localized_delocalized_coexistence', 'q1D->loc_deloc_mix', 'quant-ph'),

    # 2607.28604 - Cosmo-SPINN: Fuzzy Dark Matter Simulations
    ('initial_density_field', 'evolved_density_field', 'init_rho->evolved_rho', 'astro-ph.CO'),
    ('quantum_pressure', 'density_fluctuations', 'quantum_P->delta_rho', 'astro-ph.CO'),
    ('physics_informed_loss', 'simulation_quality', 'phys_loss->sim_quality', 'astro-ph.CO'),
    ('schrodinger_poisson_dynamics', 'generative_artifact_reduction', 'SP_dynamics->artifact_reduce', 'astro-ph.CO'),

    # 2607.28593 - Axion Inflation with Massive Abelian Gauge Field
    ('axial_coupling', 'gauge_field_helicity_amplification', 'axial_coupling->helicity_amp', 'astro-ph.CO'),
    ('gauge_field_mass', 'instability_threshold', 'm_vector->instability_thresh', 'astro-ph.CO'),
    ('vector_mass', 'curvature_perturbation_suppression', 'm_vector->zeta_suppress', 'astro-ph.CO'),
    ('xi_parameter', 'mode_amplitude', 'xi->mode_amp', 'astro-ph.CO'),
    ('gauge_field_production', 'inflaton_friction', 'gauge_prod->friction', 'astro-ph.CO'),

    # 2607.28564 - Dark Matter Constraints from Small-Scale Structure
    ('dm_free_streaming_length', 'small_scale_structure_abundance', 'free_stream->struct_abund', 'astro-ph.CO'),
    ('dm_wave_interference', 'halo_internal_structure', 'wave_interf->halo_struct', 'astro-ph.CO'),
    ('dm_self_interaction', 'halo_density_profile', 'self_interact->density_profile', 'astro-ph.CO'),
    ('probe_combination', 'dm_constraint_precision', 'multi_probe->precision', 'astro-ph.CO'),

    # 2607.28517 - Dynamical flattening of halo cusps by Q-ball DM
    ('Q_ball_interaction', 'halo_cusp_flattening', 'Qball_interact->cusp_flat', 'astro-ph.CO'),
    ('soliton_mass', 'interaction_cross_section', 'soliton_mass->cross_section', 'astro-ph.CO'),
    ('rest_mass_energy_conversion', 'inner_mass_profile', 'E_conversion->inner_profile', 'astro-ph.CO'),
    ('central_density', 'Q_ball_growth_rate', 'central_rho->Qball_growth', 'astro-ph.CO'),

    # 2607.28620 - Optimal Measurement-State Preparation via Geometric Transport
    ('mean_state_trajectory', 'squeezing_ellipse_rotation', 'trajectory->ellipse_rot', 'quant-ph'),
    ('solid_angle_path', 'geometric_phase', 'solid_angle->geo_phase', 'quant-ph'),
    ('misaligned_squeezed_input', 'measurement_optimal_state', 'misaligned->optimal', 'quant-ph'),
    ('birefringent_element', 'polarization_squeezing_control', 'birefring->squeeze_ctrl', 'quant-ph'),

    # 2607.28438 - Binary neutron stars in the next-gen era
    ('bns_merger_rate', 'gw_detection_number', 'BNS_rate->GW_detect', 'astro-ph.HE'),
    ('multi_messenger_detection', 'eos_constraint_precision', 'multi_msg->EOS_precision', 'astro-ph.HE'),
    ('multi_messenger_detection', 'hubble_constant_constraint', 'multi_msg->H0_constraint', 'astro-ph.HE'),
    ('kilonova_light_curve', 'cosmological_parameter_inference', 'kilonova_LC->cosmo_param', 'astro-ph.HE'),
    ('detector_network', 'multi_messenger_detection_yield', 'network->MM_yield', 'astro-ph.HE'),

    # 2607.28599 - Harmonic, radial, and shell stability of Einstein constraints
    ('weighted_poincare_inequality', 'harmonic_stability', 'Poincare->harmonic_stab', 'gr-qc'),
    ('weighted_korn_inequality', 'radial_stability', 'Korn->radial_stab', 'gr-qc'),
    ('weighted_hardy_inequality', 'shell_stability', 'Hardy->shell_stab', 'gr-qc'),
    ('localization_domain_size', 'stability_condition', 'local_domain->stab_cond', 'gr-qc'),
    ('einstein_constraint_localization', 'gravitational_shielding', 'constraint_local->shielding', 'gr-qc'),
]

ts = time.time()
count = 0
with open(queue_path, 'a') as f:
    for src, dst, law, domain in edges:
        item = {
            'source': 'arxiv_feed_cron',
            'type': 'edge',
            'data': {'src': src, 'dst': dst, 'law': f'feed:{law}', 'domain': domain, 'initial_s': 0.05},
            'ts': ts
        }
        f.write(json.dumps(item, ensure_ascii=False) + '\n')
        count += 1

print(f'Written {count} edges to feed_queue.jsonl')
print(f'Papers processed: 24')
print(f'Edges per paper: ~{count/24:.1f}')

# Domain breakdown
from collections import Counter
domains = Counter(d for _, _, _, d in edges)
print(f'Domain breakdown: {dict(domains)}')
