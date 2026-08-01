#!/usr/bin/env python3
"""注入同伦代数 + 因子化代数到费曼脑"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meta_cognition.feed_queue import FeedQueue

q = FeedQueue()

concepts = [
    ('homotopical_algebra', 'research', 'modern'),
    ('derived_algebraic_geometry', 'research', 'modern'),
    ('linfinity_algebra', 'research', 'modern'),
    ('derived_category', 'research', 'modern'),
    ('model_category', 'research', 'modern'),
    ('quillen_homotopy', 'research', 'modern'),
    ('higher_morphism', 'research', 'modern'),
    ('simplicial_set', 'research', 'modern'),
    ('operad', 'research', 'modern'),
    ('batalin_vilkovisky_formalism', 'research', 'modern'),
    ('brst_cohomology', 'research', 'modern'),
    ('ghost_field', 'research', 'modern'),
    ('antifield', 'research', 'modern'),
    ('antibracket', 'research', 'modern'),
    ('master_equation', 'research', 'modern'),
    ('quantum_master_equation', 'research', 'modern'),
    ('factorization_algebra', 'research', 'modern'),
    ('factorization_homology', 'research', 'modern'),
    ('cosheaf', 'research', 'modern'),
    ('prefactorization_algebra', 'research', 'modern'),
    ('costello_gwilliam_approach', 'research', 'modern'),
    ('observable_algebra', 'research', 'modern'),
    ('operator_product_expansion', 'research', 'modern'),
    ('chiral_algebra', 'research', 'modern'),
    ('vertex_operator_algebra', 'research', 'modern'),
    ('deformation_quantization', 'research', 'modern'),
    ('formal_moduli_problem', 'research', 'modern'),
    ('extended_tqft', 'research', 'modern'),
    ('cobordism_hypothesis', 'research', 'modern'),
]
for name, src, dom in concepts:
    q.feed_concept(name, source=src, domain=dom)

edges = [
    # ── 同伦代数核心 ──
    ('homotopical_algebra', 'linfinity_algebra', 'L∞-algebras: homotopy-coherent Lie algebras — natural for gauge symmetries', 'math_verified', 0.9),
    ('linfinity_algebra', 'higher_morphism', 'L∞ morphisms = homotopy-coherent maps between algebras', 'math_verified', 0.85),
    ('homotopical_algebra', 'derived_algebraic_geometry', 'Foundation of derived geometry', 'math_verified', 0.9),
    ('homotopical_algebra', 'model_category', 'Model categories axiomatize homotopy theory', 'math_verified', 0.9),
    ('linfinity_algebra', 'operad', 'L∞ = algebras over the L∞ operad', 'math_verified', 0.85),
    ('model_category', 'quillen_homotopy', 'Quillens model categories', 'math_verified', 0.9),
    ('simplicial_set', 'model_category', 'Simplicial sets = combinatorial homotopy types', 'math_verified', 0.9),

    # ── BV/BRST — 规范量子化的同伦框架 ──
    ('batalin_vilkovisky_formalism', 'gauge_field', 'BV: systematic gauge-fixing for any gauge theory', 'math_verified', 0.9),
    ('batalin_vilkovisky_formalism', 'linfinity_algebra', 'BV = L∞-algebra structure on field space', 'math_verified', 0.85),
    ('batalin_vilkovisky_formalism', 'master_equation', '(S,S)=0 — classical master equation encodes gauge invariance', 'math_verified', 0.95),
    ('master_equation', 'quantum_master_equation', 'ΔS+(S,S)/2=0 — quantum master equation (BV Laplacian)', 'math_verified', 0.95),
    ('batalin_vilkovisky_formalism', 'path_integral', 'BV makes path integral over gauge orbits well-defined', 'math_verified', 0.9),
    ('batalin_vilkovisky_formalism', 'ghost_field', 'Ghost fields encode gauge symmetry', 'math_verified', 0.9),
    ('batalin_vilkovisky_formalism', 'antifield', 'Antifields = dual to gauge parameters', 'math_verified', 0.9),
    ('batalin_vilkovisky_formalism', 'yang_mills_action', 'BV complex for YM: fields+ghosts+antifields+antighosts', 'math_verified', 0.9),
    ('brst_cohomology', 'batalin_vilkovisky_formalism', 'BRST = physical observables in BV', 'math_verified', 0.9),
    ('brst_cohomology', 'gauge_field', 'BRST: sA=dε+[A,ε] encodes gauge symmetry algebraically', 'math_verified', 0.9),
    ('antibracket', 'linfinity_algebra', 'Antibracket = L∞ structure on BV field space', 'math_verified', 0.8),

    # ── 因子化代数 ──
    ('factorization_algebra', 'costello_gwilliam_approach', 'Perturbative QFT = factorization algebra of observables', 'math_verified', 0.9),
    ('factorization_algebra', 'observable_algebra', 'QFT observables form factorization algebra on spacetime', 'math_verified', 0.9),
    ('factorization_algebra', 'operator_product_expansion', 'OPE = local structure of factorization algebra', 'math_verified', 0.9),
    ('factorization_algebra', 'perturbative_quantum_field_theory', 'Rigorous perturbative QFT framework', 'math_verified', 0.9),
    ('cosheaf', 'factorization_algebra', 'Factorization algebra = cosheaf on spacetime with multiplicativity', 'math_verified', 0.85),
    ('factorization_homology', 'factorization_algebra', 'Integrating algebras over manifolds', 'math_verified', 0.85),
    ('chiral_algebra', 'factorization_algebra', 'Factorization algebras on algebraic curves (Beilinson-Drinfeld)', 'math_verified', 0.85),
    ('vertex_operator_algebra', 'chiral_algebra', 'VOA = ℏ-deformation of chiral algebra', 'math_verified', 0.85),

    # ── 关键连接 ──
    ('batalin_vilkovisky_formalism', 'factorization_algebra', 'BV quantization = factorization algebra valued in BV complex', 'math_verified', 0.85),
    ('factorization_algebra', 'algebraic_quantum_field_theory', 'Factorization algebras generalize AQFT: local-to-global', 'math_verified', 0.85),
    ('derived_algebraic_geometry', 'batalin_vilkovisky_formalism', 'Derived geometry gives BV its natural mathematical home', 'math_verified', 0.85),
    ('factorization_algebra', 'haag_theorem', 'BV+factorization algebra: rigorous QFT without interaction picture', 'math_verified', 0.8),
    ('factorization_algebra', 'path_integral', 'Factorization algebra = algebraic structure of path integral observables', 'math_verified', 0.85),
    ('batalin_vilkovisky_formalism', 'haag_theorem', 'BV avoids interaction picture — mathematically consistent quantization', 'math_verified', 0.8),
    ('homotopical_algebra', 'gauge_field', 'Gauge symmetries = homotopy theory of mapping spaces', 'math_verified', 0.85),
    ('linfinity_algebra', 'yang_mills_action', 'YM action defines L∞-algebra on field space', 'math_verified', 0.85),
    ('formal_moduli_problem', 'linfinity_algebra', 'Formal moduli problems = L∞-algebras (Lurie-Pridham)', 'math_verified', 0.9),
    ('deformation_quantization', 'factorization_algebra', 'Deformation quantization → factorization algebra of quantum observables', 'math_verified', 0.85),
    ('derived_algebraic_geometry', 'hilbert_action', 'EH action as derived symplectic structure', 'math_verified', 0.75),
    ('cobordism_hypothesis', 'extended_tqft', 'Fully extended TQFT = (∞,n)-category of cobordisms', 'math_verified', 0.9),
    ('extended_tqft', 'factorization_algebra', 'Extended TQFT assigns factorization algebras to codim-1 strata', 'math_verified', 0.85),
]
for src, dst, law, dom, s in edges:
    q.feed_edge(src, dst, law, dom, initial_s=s)

print(f'Injected: {len(concepts)} concepts, {len(edges)} edges')
