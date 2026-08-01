#!/usr/bin/env python3
"""注入格林函数知识到费曼脑"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meta_cognition.feed_queue import FeedQueue

q = FeedQueue()

concepts = [
    ('greens_function', 'research', 'quantum'),
    ('propagator', 'research', 'quantum'),
    ('feynman_propagator', 'research', 'quantum'),
    ('retarded_greens_function', 'research', 'quantum'),
    ('advanced_greens_function', 'research', 'quantum'),
    ('generating_functional', 'research', 'quantum'),
    ('schwinger_dyson_equation', 'research', 'quantum'),
    ('connected_greens_function', 'research', 'quantum'),
    ('one_particle_irreducible', 'research', 'quantum'),
    ('effective_action', 'research', 'quantum'),
    ('wick_theorem', 'research', 'quantum'),
    ('time_ordered_product', 'research', 'quantum'),
    ('dyson_series', 'research', 'quantum'),
    ('correlation_function', 'research', 'quantum'),
    ('ward_takahashi_identity', 'research', 'quantum'),
    ('kallen_lehmann_spectral_representation', 'research', 'quantum'),
    ('lsz_reduction_formula', 'research', 'quantum'),
    ('spectral_density', 'research', 'quantum'),
    ('propagator_as_homotopy', 'research', 'modern'),
    ('homotopy_transfer_theorem', 'research', 'modern'),
]
for name, src, dom in concepts:
    q.feed_concept(name, source=src, domain=dom)

edges = [
    # ── 格林函数定义 ──
    ('greens_function', 'propagator', 'Green\'s function = propagator = inverse of kinetic operator', 'math_verified', 0.95),
    ('greens_function', 'feynman_propagator', 'Feynman propagator = time-ordered vacuum expectation ⟨0|Tφ(x)φ(y)|0⟩', 'math_verified', 0.95),
    ('feynman_propagator', 'path_integral', 'ΔF(x-y) = ∫Dφ φ(x)φ(y) e^{iS}/Z', 'math_verified', 0.9),
    ('greens_function', 'retarded_greens_function', 'Retarded: G_R(t) = 0 for t < 0 — causal propagation', 'math_verified', 0.9),
    ('greens_function', 'advanced_greens_function', 'Advanced: G_A(t) = 0 for t > 0 — anti-causal', 'math_verified', 0.9),
    ('retarded_greens_function', 'feynman_propagator', 'ΔF = θ(t)Δ+ + θ(-t)Δ- — Feynman = retarded+advanced decomposition', 'math_verified', 0.9),

    # ── 生成泛函 ──
    ('generating_functional', 'greens_function', 'Z[J]=∫Dφ e^{iS+i∫Jφ} — Green\'s functions = functional derivatives', 'math_verified', 0.95),
    ('generating_functional', 'path_integral', 'Z[J] = partition function with source J', 'math_verified', 0.95),
    ('generating_functional', 'connected_greens_function', 'W[J] = -i log Z[J] — generating functional of connected Green\'s functions', 'math_verified', 0.9),
    ('connected_greens_function', 'one_particle_irreducible', 'Γ[φ] = Legendre transform of W[J] — 1PI effective action', 'math_verified', 0.9),
    ('one_particle_irreducible', 'effective_action', 'Effective action Γ[φ] = quantum-corrected classical action', 'math_verified', 0.9),
    ('effective_action', 'action', 'Γ[φ] → S[φ] in classical limit ℏ→0', 'math_verified', 0.9),

    # ── 联系因子化代数 ──
    ('time_ordered_product', 'greens_function', 'T-product: time ordering of field operators — the algebra of Green\'s functions', 'math_verified', 0.9),
    ('time_ordered_product', 'factorization_algebra', 'Time-ordered product = factorization algebra structure on observables', 'math_verified', 0.85),
    ('time_ordered_product', 'operator_product_expansion', 'OPE = short-distance expansion of T-products', 'math_verified', 0.85),
    ('greens_function', 'factorization_algebra', 'Green\'s functions = structure constants of the factorization algebra', 'math_verified', 0.8),
    ('effective_action', 'factorization_algebra', 'Effective action Γ defines the minimal model of the factorization algebra', 'math_verified', 0.8),

    # ── 联系BV/同伦 ──
    ('greens_function', 'batalin_vilkovisky_formalism', 'BV propagator = homotopy between inclusion and projection of harmonic forms', 'math_verified', 0.85),
    ('propagator_as_homotopy', 'greens_function', 'Propagator = homotopy operator: P = ∂h + h∂ where h = Green\'s function', 'math_verified', 0.85),
    ('propagator_as_homotopy', 'linfinity_algebra', 'Homotopy transfer: L∞ structure transfers along propagator (homotopy transfer theorem)', 'math_verified', 0.85),
    ('homotopy_transfer_theorem', 'propagator_as_homotopy', 'HTT: propagator transfers algebraic structure to cohomology', 'math_verified', 0.9),
    ('homotopy_transfer_theorem', 'effective_action', 'Effective action = homotopy transfer of classical action along propagator', 'math_verified', 0.85),
    ('homotopy_transfer_theorem', 'factorization_algebra', 'HTT computes factorization algebra of effective theory from classical data', 'math_verified', 0.8),
    ('batalin_vilkovisky_formalism', 'propagator_as_homotopy', 'BV propagator implements the homotopy between gauge-fixed and physical states', 'math_verified', 0.85),

    # ── 微扰展开 ──
    ('dyson_series', 'greens_function', 'Dyson series = perturbative expansion of Green\'s functions in coupling', 'math_verified', 0.9),
    ('dyson_series', 'feynman_propagator', 'Each term in Dyson series = Feynman diagram with propagators', 'math_verified', 0.9),
    ('wick_theorem', 'greens_function', 'Wick theorem: T-ordered product = sum over all contractions (normal ordering)', 'math_verified', 0.9),
    ('wick_theorem', 'time_ordered_product', 'T(φ1...φn) = :φ1...φn: + all contractions', 'math_verified', 0.9),
    ('correlation_function', 'greens_function', 'Correlation function = n-point Green\'s function ⟨φ(x1)...φ(xn)⟩', 'math_verified', 0.9),

    # ── 谱表示与物理 ──
    ('kallen_lehmann_spectral_representation', 'greens_function', 'Kallen-Lehmann: exact propagator = integral over spectral density', 'math_verified', 0.9),
    ('kallen_lehmann_spectral_representation', 'spectral_density', 'ρ(μ²) = spectral density encodes physical particle content', 'math_verified', 0.9),
    ('kallen_lehmann_spectral_representation', 'spontaneous_symmetry_breaking', 'SSB: Goldstone pole in spectral density at p²=0', 'math_verified', 0.85),
    ('lsz_reduction_formula', 'greens_function', 'LSZ: S-matrix elements = residues of poles in Green\'s functions', 'math_verified', 0.9),
    ('lsz_reduction_formula', 'correlation_function', '⟨out|S|in⟩ = amputated Green\'s function at mass shell', 'math_verified', 0.9),
    ('ward_takahashi_identity', 'greens_function', 'Ward identity: gauge symmetry constraint on Green\'s functions = current conservation', 'math_verified', 0.9),
    ('ward_takahashi_identity', 'gauge_field', '∂μ⟨0|T jμ(x)...|0⟩ = 0 — gauge invariance of correlators', 'math_verified', 0.9),
    ('schwinger_dyson_equation', 'greens_function', 'Schwinger-Dyson: exact equations of motion for Green\'s functions — non-perturbative', 'math_verified', 0.9),
    ('schwinger_dyson_equation', 'effective_action', 'δΓ/δφ = ⟨δS/δφ⟩ — SD = equations for effective action', 'math_verified', 0.9),

    # ── 联系Haag/AQFT ──
    ('greens_function', 'haag_theorem', 'Haag theorem: free and interacting Green\'s functions cannot be connected by unitary transformation', 'math_verified', 0.85),
    ('greens_function', 'gelfand_naimark_segal_construction', 'GNS: vacuum expectation values = Green\'s functions define the representation', 'math_verified', 0.85),
    ('greens_function', 'algebraic_quantum_field_theory', 'AQFT: physical content = all Green\'s functions = state on algebra of observables', 'math_verified', 0.85),
]
for src, dst, law, dom, s in edges:
    q.feed_edge(src, dst, law, dom, initial_s=s)

print(f'Injected: {len(concepts)} concepts, {len(edges)} edges')
