#!/usr/bin/env python3
"""费曼脑论文摄入 — 从本次 arXiv 新论文提取物理因果边, 注入 feed_queue.jsonl"""
import json, os, sys, time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
from meta_cognition.feed_queue import FeedQueue

# (arxiv_id, [(src, dst, confidence), ...])  — 每篇 3-10 条
EDGES = {
    "2608.13557v1": [
        ("scalar_potential", "thermal_confinement_transition", 0.7),
        ("dimension_d", "supercooling_suppression", 0.7),
        ("speed_of_sound", "maximum_supercooling", 0.8),
        ("black_brane_geometry", "deconfined_phase", 0.8),
        ("minimal_temperature", "maximum_supercooling", 0.7),
        ("holographic_duality", "predictive_structure", 0.6),
    ],
    "2608.13542v1": [
        ("quasi_conserved_observables", "relaxation_timescale", 0.8),
        ("fast_relaxation_timescale", "systematic_expansion", 0.8),
        ("linearized_causal_kinetic_theory", "symmetric_hyperbolic_dynamics", 0.9),
        ("slow_degrees_of_freedom", "transient_hydrodynamic_universality_class", 0.7),
        ("microscopic_theory", "symmetry_constraints", 0.7),
        ("higher_order_corrections", "positivity_constraints", 0.6),
    ],
    "2608.13529v1": [
        ("self_accelerating_branch", "kinetic_coefficient_vanishing", 0.9),
        ("kinetic_coefficient", "strong_coupling_strength", 0.9),
        ("minimal_matter", "gravitational_vector_mode_health", 0.8),
        ("branch_choice", "perturbative_health", 0.8),
        ("scalar_field", "transverse_perturbation", 0.7),
        ("friedmann_equation", "shift_constraint_cancellation", 0.6),
    ],
    "2608.13378v1": [
        ("nonlinear_electrodynamics_correction", "black_hole_solution", 0.9),
        ("thermal_fluctuations", "entropy_corrections", 0.9),
        ("entropy_corrections", "enthalpy", 0.85),
        ("entropy_corrections", "specific_heat_divergence", 0.8),
        ("specific_heat_divergence", "second_order_phase_transition", 0.8),
        ("quantum_corrections", "black_hole_stability", 0.7),
    ],
    "2608.13319v1": [
        ("boundary_metric", "renormalized_generating_functional", 0.9),
        ("microscopic_coupling_data", "boundary_response", 0.8),
        ("holographic_observables", "higher_dimensional_parameters", 0.7),
        ("weyl_anomaly", "anomaly_coefficients", 0.7),
        ("scalar_source", "one_point_functions", 0.7),
        ("boundary_covariant_radial_hierarchy", "variational_problem", 0.6),
    ],
    "2608.13289v1": [
        ("metric_tensor", "transformed_metric_tensor", 0.9),
        ("auxiliary_scalar_field", "localized_forward_map", 0.8),
        ("nonpolynomial_projector", "differential_obstruction", 0.8),
        ("ricci_scalar", "conformal_factor", 0.8),
        ("cauchy_data", "branchwise_functional_inverse", 0.7),
        ("curvature_dependence", "local_metric_change", 0.6),
    ],
    "2608.13282v1": [
        ("bumblebee_vacuum_expectation_value", "gravitational_wave_propagation_amplitude", 0.7),
        ("bumblebee_vacuum_expectation_value", "cosmic_expansion", 0.8),
        ("gravitational_wave_standard_sirens", "luminosity_distance", 1.0),
        ("supernova_data", "hubble_constant_precision", 0.8),
        ("lorentz_violation_parameter", "gravitational_wave_form", 0.6),
        ("evolving_vacuum_expectation_value", "redshift_dependence", 0.6),
    ],
    "2608.13347v1": [
        ("turnaround_radius", "matter_dark_energy_degeneracy_breaking", 0.8),
        ("outer_density_profile", "turnaround_radius", 0.7),
        ("simplifying_assumptions", "systematic_error", 0.7),
        ("excursion_set_theory", "analytic_density_profile", 0.8),
        ("clustering_parameter", "double_distribution", 0.6),
        ("numerical_mode_estimate", "profile_divergence", 0.6),
    ],
    "2608.13346v1": [
        ("scalar_field_mass", "oscillation_timescale", 1.0),
        ("oscillation_onset", "numerical_intractability", 0.8),
        ("averaging_technique", "fluid_equations", 0.8),
        ("scalar_field", "field_evolution", 0.9),
        ("hubble_parameter", "oscillation_condition", 0.7),
        ("interacting_dark_matter", "averaging_capability", 0.6),
    ],
    "2608.13257v1": [
        ("interferogram", "spectrum", 1.0),
        ("polarization_difference", "interference_pattern", 0.8),
        ("cmb_spectrum", "spectral_distortions", 0.9),
        ("ray_tracing", "optical_configuration", 0.8),
        ("frequency_band", "focal_plane_design", 0.7),
        ("gaussian_beam_analysis", "beam_propagation", 0.6),
    ],
    "2608.13225v1": [
        ("instrument_optical_system", "cmb_spectral_distortion_measurement", 0.5),
        ("dichroic", "frequency_subband_split", 0.8),
        ("subkelvin_detector", "detector_sensitivity", 0.7),
        ("systematic_effects", "measurement_precision", 0.7),
        ("ray_tracing", "optical_configuration", 0.8),
        ("calibration_source", "interferometer_input", 0.6),
    ],
    "2608.13206v1": [
        ("superhorizon_curvature_perturbation", "primordial_black_hole_formation", 0.8),
        ("radiation_dominated_universe", "hydrodynamic_evolution", 0.7),
        ("scale_factor", "cosmic_time_step", 0.9),
        ("curvature_profile_amplitude", "collapse_threshold", 0.8),
        ("critical_collapse", "critical_exponent", 0.7),
        ("accretion", "black_hole_mass_growth", 0.7),
    ],
    "2608.13185v1": [
        ("cryogenic_architecture", "instrument_temperature", 0.9),
        ("instrument_temperature", "measurement_sensitivity", 0.8),
        ("passive_cooling_chain", "thermal_stage_temperature", 0.8),
        ("vgroove_radiator", "intermediate_temperature", 0.7),
        ("adiabatic_demagnetization_refrigerator", "subkelvin_temperature", 0.8),
        ("detector_temperature", "noise_level", 0.6),
    ],
}


def _norm(s: str) -> str:
    return s.strip().lower().replace(" ", "_")


def main():
    data_dir = os.path.join(_ROOT, "data")
    fq = FeedQueue(data_dir)

    papers_fed = 0
    total_edges = 0

    for arxiv_id, edges in EDGES.items():
        seen = set()
        paper_edges = 0
        for src, dst, conf in edges:
            src_n, dst_n = _norm(src), _norm(dst)
            if not src_n or not dst_n or src_n == dst_n:
                continue
            pair = (src_n, dst_n)
            if pair in seen:
                continue
            seen.add(pair)
            initial_s = round(0.02 + conf * 0.06, 3)
            fq.feed_edge(
                src=src_n, dst=dst_n,
                law=f"arxiv:{arxiv_id}",
                source=f"arxiv:{arxiv_id}",
                domain="arxiv_research",
                initial_s=initial_s,
            )
            paper_edges += 1
            total_edges += 1
        if paper_edges:
            papers_fed += 1
            print(f"  [{arxiv_id}] +{paper_edges} edges")

    print(f"\n[DONE] fed {papers_fed} papers -> {total_edges} causal edges")


if __name__ == "__main__":
    main()
