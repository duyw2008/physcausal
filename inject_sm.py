#!/usr/bin/env python3
"""注入标准模型结构化知识到费曼脑 — Route A+B"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from meta_cognition.feed_queue import FeedQueue

q = FeedQueue()

# ═══════════════════════════════════════════════════════
# Route A: 标准模型拉氏量分解
# ═══════════════════════════════════════════════════════

# ── 核心概念节点 ──
concepts = [
    ("standard_model_lagrangian", "research", "modern"),
    ("yang_mills_action", "research", "modern"),
    ("hilbert_action", "research", "general_relativity"),
    ("dirac_action", "research", "quantum"),
    ("higgs_action", "research", "quantum"),
    ("yukawa_action", "research", "quantum"),
    ("chern_simons_action", "research", "modern"),
    ("yang_mills_equation", "research", "modern"),
    ("einstein_field_equation", "research", "general_relativity"),
    ("dirac_equation", "research", "quantum"),
    ("klein_gordon_equation", "research", "quantum"),
    ("gauge_covariant_derivative", "research", "modern"),
    ("field_strength_tensor", "research", "modern"),
    ("gauge_group_su3_su2_u1", "research", "modern"),
    ("electroweak_unification", "research", "modern"),
    ("quark_sector", "research", "modern"),
    ("lepton_sector", "research", "modern"),
    ("spontaneous_symmetry_breaking", "research", "quantum"),
    ("goldstone_boson", "research", "quantum"),
    ("w_boson_mass", "research", "modern"),
    ("z_boson_mass", "research", "modern"),
    ("photon_mass_zero", "research", "modern"),
]
for name, src, dom in concepts:
    q.feed_concept(name, source=src, domain=dom)

# ── 关键边: 拉氏量 → 作用量 → 运动方程 ──
edges = [
    # 标准模型拉氏量分解
    ("standard_model_lagrangian", "yang_mills_action", "SM=YM+Dirac+Higgs+Yukawa", "math_verified", 0.9),
    ("standard_model_lagrangian", "dirac_action", "SM=YM+Dirac+Higgs+Yukawa", "math_verified", 0.9),
    ("standard_model_lagrangian", "higgs_action", "SM=YM+Dirac+Higgs+Yukawa", "math_verified", 0.9),
    ("standard_model_lagrangian", "yukawa_action", "SM=YM+Dirac+Higgs+Yukawa", "math_verified", 0.9),
    ("standard_model_lagrangian", "hilbert_action", "SM+GR: Einstein-Hilbert", "math_verified", 0.9),

    # δS=0 → 运动方程
    ("yang_mills_action", "yang_mills_equation", "δS_YM=0→DμFμν=Jν", "math_verified", 0.95),
    ("hilbert_action", "einstein_field_equation", "δS_EH=0→Gμν=8πGTμν", "math_verified", 0.95),
    ("dirac_action", "dirac_equation", "δS_D=0→(iγμDμ-m)ψ=0", "math_verified", 0.95),
    ("higgs_action", "spontaneous_symmetry_breaking", "δS_H=0→Mexican hat potential", "math_verified", 0.9),
    ("yukawa_action", "fermion_mass", "δS_Y→mf=hf v/√2", "math_verified", 0.9),

    # 规范结构
    ("gauge_covariant_derivative", "yang_mills_action", "Dμ=∂μ+igAμ", "math_verified", 0.9),
    ("field_strength_tensor", "yang_mills_action", "Fμν=[Dμ,Dν]/ig", "math_verified", 0.9),
    ("gauge_group_su3_su2_u1", "yang_mills_action", "SU(3)×SU(2)×U(1)", "math_verified", 0.95),

    # Higgs 机制
    ("scalar_field", "higgs_action", "Higgs doublet φ", "math_verified", 0.9),
    ("spontaneous_symmetry_breaking", "w_boson_mass", "W± eat Goldstone→massive", "math_verified", 0.9),
    ("spontaneous_symmetry_breaking", "z_boson_mass", "Z eats Goldstone→massive", "math_verified", 0.9),
    ("spontaneous_symmetry_breaking", "photon_mass_zero", "U(1)EM unbroken→massless", "math_verified", 0.9),

    # Electroweak 统一
    ("gauge_group_su3_su2_u1", "electroweak_unification", "SU(2)L×U(1)Y→U(1)EM", "math_verified", 0.95),
    ("electroweak_unification", "w_boson_mass", "W mass from Higgs mechanism", "math_verified", 0.9),
    ("electroweak_unification", "z_boson_mass", "Z mass from Higgs mechanism", "math_verified", 0.9),

    # 作用量 → δS=0（核心连接）
    ("yang_mills_action", "action", "S_YM=∫Tr(F∧⋆F)", "math_verified", 0.9),
    ("hilbert_action", "action", "S_EH=∫R√(-g)", "math_verified", 0.9),
    ("dirac_action", "action", "S_D=∫ψ̄(iγD-m)ψ", "math_verified", 0.9),

    # 费曼路径积分（量子化）
    ("path_integral", "action", "Z=∫Dφ exp(iS/ħ)", "math_verified", 0.95),
]
for src, dst, law, dom, s in edges:
    q.feed_edge(src, dst, law, dom, initial_s=s)

# ═══════════════════════════════════════════════════════
# Route B: 纤维丛 / 联络 — gauge = connection
# ═══════════════════════════════════════════════════════

concepts_b = [
    ("principal_bundle", "research", "modern"),
    ("connection_one_form", "research", "modern"),
    ("curvature_two_form", "research", "modern"),
    ("tangent_bundle", "research", "general_relativity"),
    ("levi_civita_connection", "research", "general_relativity"),
    ("riemann_curvature", "research", "general_relativity"),
    ("spin_connection", "research", "quantum"),
    ("fiber_bundle", "research", "modern"),
    ("non_commutative_geometry", "research", "modern"),
    ("spectral_triple", "research", "modern"),
]
for name, src, dom in concepts_b:
    q.feed_concept(name, source=src, domain=dom)

edges_b = [
    # 核心类比: 规范场 = 主丛联络
    ("gauge_field", "connection_one_form", "gauge potential Aμ = connection ω", "math_verified", 0.9),
    ("field_strength_tensor", "curvature_two_form", "Fμν = curvature Ω", "math_verified", 0.9),
    ("gauge_covariant_derivative", "connection_one_form", "Dμ = d + Aμ", "math_verified", 0.9),
    ("principal_bundle", "gauge_field", "Gauge field lives on principal bundle", "math_verified", 0.85),
    ("principal_bundle", "connection_one_form", "Connection on principal bundle", "math_verified", 0.9),
    ("connection_one_form", "curvature_two_form", "Ω = dω + ω∧ω", "math_verified", 0.9),

    # 引力 = 切丛联络
    ("spacetime_curvature", "levi_civita_connection", "GR connection = Christoffel Γ", "math_verified", 0.9),
    ("levi_civita_connection", "riemann_curvature", "Rρσμν = ∂Γ-∂Γ+ΓΓ-ΓΓ", "math_verified", 0.9),
    ("tangent_bundle", "spacetime_curvature", "Gravity = curvature of tangent bundle", "math_verified", 0.85),
    ("tangent_bundle", "levi_civita_connection", "Levi-Civita on tangent bundle", "math_verified", 0.9),

    # 统一视角: 所有力 = 联络
    ("connection_one_form", "levi_civita_connection", "All forces = connections on bundles", "math_verified", 0.85),
    ("curvature_two_form", "riemann_curvature", "All field strengths = curvatures", "math_verified", 0.85),
]

for src, dst, law, dom, s in edges_b:
    q.feed_edge(src, dst, law, dom, initial_s=s)

print(f"Injected: {len(concepts)+len(concepts_b)} concepts, {len(edges)+len(edges_b)} edges")
print("Feed queue ready. Brain will consume on next breathe cycle.")
