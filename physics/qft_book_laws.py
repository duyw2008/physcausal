"""
一读就懂的量子场论 → 白名单加料 (2026-08-27)

来源: 用户 QFT 教育书 (6717 行, 8 部分) 的核心概念 + 因果链。
加入白名单 = 概念进 legal 集 (physics_passed 闸门), 因果方向给脑当种子。
每条定律 = 书的一个叙事单元 (给路径不给结论, 造物主原则)。

持久化: 注册到 library, 重启后 colony 自动加载。
"""
from physics.laws import PhysicsLaw, ConstraintType


# ═══════════════════════════════════════════════════════════════
# 书的核心因果链 (每一条 = 书的一个叙事单元)
# ═══════════════════════════════════════════════════════════════

QFT_BOOK_LAWS = [
    # ── 第一部分: QM 局限 → 必须有场 (1.1-1.5) ──
    PhysicsLaw("QM Needs Field", "qft", r"QM 态空间局限 + 相对论 → 场",
               ["quantum_mechanics", "relativity"], ["quantum_field"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("quantum_mechanics", "quantum_field"), ("relativity", "quantum_field"),
                ("vacuum_fluctuation", "quantum_field")]),
    PhysicsLaw("Field Excitation", "qft", r"粒子 = 场的激发态",
               ["quantum_field", "field"], ["particle", "boson", "fermion"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("quantum_field", "particle"), ("quantum_field", "boson"),
                ("quantum_field", "fermion")]),

    # ── 第二部分: 经典场论 (2.2-2.7) ──
    PhysicsLaw("Field Lagrangian", "qft", r"L → L(φ,∂φ) 拉格朗日密度",
               ["lagrangian", "lagrangian_density", "field"], ["field_equation"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("lagrangian", "lagrangian_density"), ("lagrangian_density", "field_equation")]),
    PhysicsLaw("EulerLagrange Field", "qft", r"δS=0 → 场的运动方程",
               ["lagrangian_density", "action", "euler_lagrange"], ["field_equation"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("action", "euler_lagrange"), ("euler_lagrange", "field_equation"),
                ("lagrangian_density", "euler_lagrange")]),
    PhysicsLaw("Noether Theorem", "qft", r"连续对称性 → 守恒流 → 守恒荷",
               ["symmetry", "noether_current"], ["conserved_charge"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("symmetry", "noether_current"), ("noether_current", "conserved_charge")]),

    # ── 第三部分: 量子化 (3.1-3.5) ──
    PhysicsLaw("Canonical Quantization", "qft", r"经典变量 → 算符 + 对易关系",
               ["field", "canonical_quantization", "commutation_relation"], ["quantum_field"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("field", "canonical_quantization"), ("canonical_quantization", "quantum_field"),
                ("commutation_relation", "quantum_field")]),
    PhysicsLaw("KleinGordon", "qft", r"标量场量子化",
               ["quantum_field", "klein_gordon"], ["scalar_field"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("quantum_field", "klein_gordon"), ("klein_gordon", "scalar_field")]),
    PhysicsLaw("Dirac Field", "qft", r"旋量场 → 费米子",
               ["quantum_field", "dirac_field", "spinor_field"], ["fermion", "chirality", "helicity"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("quantum_field", "dirac_field"), ("dirac_field", "spinor_field"),
                ("spinor_field", "fermion"), ("spinor_field", "chirality"),
                ("spinor_field", "helicity")]),
    PhysicsLaw("Maxwell Field", "qft", r"矢量场 → 光子",
               ["quantum_field", "maxwell_field", "vector_field"], ["photon", "gauge_boson"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("quantum_field", "maxwell_field"), ("maxwell_field", "vector_field"),
                ("vector_field", "photon"), ("vector_field", "gauge_boson")]),
    PhysicsLaw("Vacuum Energy", "qft", r"零点能 → 真空涨落",
               ["quantum_field", "zero_point_energy"], ["vacuum_fluctuation"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("quantum_field", "zero_point_energy"), ("zero_point_energy", "vacuum_fluctuation")]),

    # ── 第四部分: 相互作用 (4.1-4.8) ──
    PhysicsLaw("Interaction", "qft", r"相互作用拉格朗日量 → 微扰论",
               ["lagrangian_density", "perturbation_theory"], ["interaction_lagrangian"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("lagrangian_density", "interaction_lagrangian"),
                ("interaction_lagrangian", "perturbation_theory")]),
    PhysicsLaw("Propagator", "qft", r"传播子 = 格林函数",
               ["field", "feynman_propagator"], ["green_function"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("field", "feynman_propagator"), ("feynman_propagator", "green_function")]),
    PhysicsLaw("Feynman Rules", "qft", r"微扰论 → 费曼规则 → 费曼图",
               ["perturbation_theory", "feynman_rule"], ["feynman_diagram"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("perturbation_theory", "feynman_rule"), ("feynman_rule", "feynman_diagram")]),
    PhysicsLaw("Wick Theorem", "qft", r"编时乘积 → 正规序 + 收缩",
               ["perturbation_theory", "wick_theorem"], ["correlation_function"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("perturbation_theory", "wick_theorem"), ("wick_theorem", "correlation_function")]),
    PhysicsLaw("S Matrix", "qft", r"费曼图 → 散射振幅 → S矩阵 → 截面",
               ["feynman_diagram", "scattering_amplitude", "s_matrix", "lsz_reduction"],
               ["cross_section", "unitarity"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("feynman_diagram", "scattering_amplitude"), ("scattering_amplitude", "s_matrix"),
                ("lsz_reduction", "scattering_amplitude"), ("s_matrix", "cross_section"),
                ("s_matrix", "unitarity"), ("correlation_function", "lsz_reduction")]),
    PhysicsLaw("Relativistic Symmetry", "qft", r"洛伦兹不变性 + 定域性 + 因果性",
               ["lorentz_invariance", "locality", "causality", "unitarity"], ["s_matrix"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("lorentz_invariance", "s_matrix"), ("locality", "s_matrix"),
                ("causality", "s_matrix"), ("unitarity", "s_matrix")]),

    # ── 第五部分: 重整化 (5.1-5.7) ──
    PhysicsLaw("Renormalization", "qft", r"发散 → 正规化 → 重整化 → 有效场论",
               ["perturbation_theory", "renormalization", "dimensional_regularization"],
               ["effective_field_theory"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("perturbation_theory", "renormalization"),
                ("renormalization", "effective_field_theory"),
                ("dimensional_regularization", "renormalization")]),
    PhysicsLaw("Renormalization Group", "qft", r"重整化群 → 跑动耦合 → β函数",
               ["renormalization", "renormalization_group"], ["running_coupling", "beta_function"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("renormalization", "renormalization_group"),
                ("renormalization_group", "running_coupling"),
                ("running_coupling", "beta_function")]),

    # ── 第六部分: 规范场论 (6.0-6.6) ──
    PhysicsLaw("Gauge Principle", "qft", r"局域对称性 → 规范场 → 规范玻色子 (力)",
               ["gauge_symmetry", "gauge_invariance", "gauge_field"], ["gauge_boson"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("gauge_symmetry", "gauge_invariance"), ("gauge_invariance", "gauge_field"),
                ("gauge_field", "gauge_boson")]),
    PhysicsLaw("YangMills", "qft", r"非阿贝尔规范 → 杨-米尔斯",
               ["gauge_field", "yang_mills"], ["gauge_boson"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("gauge_field", "yang_mills"), ("yang_mills", "gauge_boson")]),
    PhysicsLaw("Higgs Mechanism", "qft", r"自发破缺 → 希格斯机制 → 质量",
               ["spontaneous_symmetry_breaking", "higgs_mechanism", "higgs_field"],
               ["mass", "w_boson", "z_boson"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("spontaneous_symmetry_breaking", "higgs_mechanism"),
                ("higgs_mechanism", "higgs_field"), ("higgs_mechanism", "mass"),
                ("higgs_mechanism", "w_boson"), ("higgs_mechanism", "z_boson")]),
    PhysicsLaw("Standard Model", "qft", r"规范场 → 标准模型",
               ["gauge_field", "higgs_mechanism", "standard_model"], ["gauge_boson", "fermion"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("gauge_field", "standard_model"), ("higgs_mechanism", "standard_model"),
                ("standard_model", "gauge_boson"), ("standard_model", "fermion")]),

    # ── 第七部分: 路径积分 (7.1) ──
    PhysicsLaw("Path Integral", "qft", r"作用量 → 路径积分 → 配分函数",
               ["action", "path_integral", "generating_functional"], ["partition_function"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("action", "path_integral"), ("path_integral", "generating_functional"),
                ("generating_functional", "partition_function"),
                ("partition_function", "correlation_function")]),

    # ── 第八部分: 前沿 (8.1-8.4, 概念注册为主, 因果方向保持保守) ──
    PhysicsLaw("QFT Frontier", "qft", r"前沿概念: 反常/禁闭/超对称/大统一",
               ["anomaly", "quark_confinement", "lattice_qcd", "wilson_loop",
                "supersymmetry", "grand_unification", "conformal_field",
                "topological_field", "operator_product_expansion",
                "anomalous_dimension", "composite_operator", "feynman_parameter",
                "brst", "wightman", "gauge_fixing", "ghost_field"],
               [], ConstraintType.DAG_EDGE, lambda: 1.0,
               [("gauge_fixing", "ghost_field"), ("ghost_field", "brst"),
                ("lattice_qcd", "quark_confinement"), ("wilson_loop", "quark_confinement")]),

    # ── 多方程身份增强 (2026-08-27): 关键概念跨独立定律出现 ──
    # 同一概念在多个独立方程中扮演角色 → 脑通过多元约束收敛深层语义
    # (类比词向量: 词义 = 它出现的所有上下文; 物理: mass 在力学/GR/量子三面)
    PhysicsLaw("Lagrangian Origin", "qft", r"拉格朗日密度 → 各类场方程",
               ["lagrangian_density"], ["klein_gordon", "dirac_field", "maxwell_field",
                                        "noether_current", "gauge_field"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("lagrangian_density", "klein_gordon"), ("lagrangian_density", "dirac_field"),
                ("lagrangian_density", "maxwell_field"), ("lagrangian_density", "noether_current"),
                ("lagrangian_density", "gauge_field")]),
    PhysicsLaw("Quantization Origin", "qft", r"量子化 → 零点能/传播子",
               ["canonical_quantization", "path_integral"],
               ["zero_point_energy", "feynman_propagator", "commutation_relation"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("canonical_quantization", "zero_point_energy"),
                ("path_integral", "feynman_propagator"),
                ("canonical_quantization", "commutation_relation")]),
    PhysicsLaw("Renormalization Context", "qft", r"有效场论 → 重整化群",
               ["effective_field_theory"], ["renormalization_group", "running_coupling"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("effective_field_theory", "renormalization_group"),
                ("effective_field_theory", "running_coupling")]),
    PhysicsLaw("Gauge Family", "qft", r"规范场家族: 光子/W/Z/胶子",
               ["gauge_field", "gauge_boson"], ["photon", "w_boson", "z_boson", "gluon"],
               ConstraintType.DAG_EDGE, lambda: 1.0,
               [("gauge_field", "photon"), ("gauge_field", "w_boson"),
                ("gauge_field", "z_boson"), ("gauge_field", "gluon"),
                ("gauge_boson", "photon"), ("gauge_boson", "w_boson"),
                ("gauge_boson", "z_boson"), ("gauge_boson", "gluon")]),
]


def register_qft_book() -> int:
    """注册书定律进 library (幂等: 已注册的跳过)。"""
    existing = set()
    from physics.laws import library
    for law in library._laws:
        for src, dst in law.causal_direction:
            existing.add((src, dst))
    added = 0
    for law in QFT_BOOK_LAWS:
        new = [d for d in law.causal_direction if d not in existing]
        if new:
            library._laws.append(law)
            added += 1
            for d in new:
                existing.add(d)
    if added:
        print(f"📖 QFT书加料: +{added} 定律, +{sum(len(l.causal_direction) for l in QFT_BOOK_LAWS)} 因果方向")
    return added
