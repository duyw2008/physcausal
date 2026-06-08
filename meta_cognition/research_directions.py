"""
研究议程 — 让物理学家选择方向，不再随机瞎跑

6 个当前热门方向 + 3 个 PhysCausal 特有方向。
每个方向包含:
  - 核心问题
  - 关键变量 (偏置探索)
  - 难度/风险
  - 为什么值得做
"""

from __future__ import annotations
from typing import Dict, List, Optional
import os
import json

# ── 研究方向库 ──

RESEARCH_DIRECTIONS: List[Dict] = [
    {
        "id": "quantum_gravity",
        "name": "量子引力与时空因果结构",
        "tag": "QG",
        "core_question": "时空在普朗克尺度是否有离散因果结构？",
        "why_now": "CDT/因果集/LQG 三线并进，都指向'因果优先于度规'。PhysCausal 的因果图天然适合检验这个假说。",
        "key_variables": ["spacetime_curvature", "geodesic_path", "quantum_amplitude",
                          "compact_dimension", "higher_d_metric", "causal_order"],
        "key_domains": ["geometry", "quantum", "general_relativity"],
        "key_lenses": ["path_integral", "geometric_identity", "action_root"],
        "difficulty": 5,
        "reward": 5,
        "open_problems": [
            "黑洞信息悖论中的因果结构",
            "AdS/CFT 体-边界因果关系",
            "因果集是否能在低能极限恢复爱因斯坦方程",
        ],
    },
    {
        "id": "quantum_foundations",
        "name": "量子基础与测量问题",
        "tag": "QM",
        "core_question": "测量是否是一个因果过程？",
        "why_now": "量子基础正在从哲学问题变成可实验问题。因果推断可以为 Bell/CHSH/坍缩模型提供新工具。",
        "key_variables": ["wave_function", "collapse_probability", "measurement",
                          "post_measurement_state", "mixed_state", "entanglement"],
        "key_domains": ["quantum", "quantum_mechanics"],
        "key_lenses": ["measurement_problem", "path_integral", "bootstrap"],
        "difficulty": 5,
        "reward": 4,
        "open_problems": [
            "坍缩是物理过程还是知识更新？",
            "多世界 vs 客观坍缩：因果检验能区分吗？",
            "Wigner 朋友悖论的因果结构",
        ],
    },
    {
        "id": "emergence_arrow",
        "name": "涌现与时间箭头",
        "tag": "EM",
        "core_question": "宏观不可逆性如何从微观可逆定律中涌现？",
        "why_now": "信息热力学和量子多体系统提供了新的因果视角。PhysCausal 的粗粒化模块天然适配。",
        "key_variables": ["entropy", "temperature", "phase", "density",
                          "order_parameter", "coarse_grained_state"],
        "key_domains": ["thermodynamics", "quantum", "classical"],
        "key_lenses": ["arrow_of_time", "stability_structure", "action_root"],
        "difficulty": 3,
        "reward": 4,
        "open_problems": [
            "初始条件低熵的宇宙学根源",
            "量子热化 (ETH) 的因果机制",
            "粗粒化是否丢失了可逆信息？",
        ],
    },
    {
        "id": "it_from_bit",
        "name": "信息本原论 (It from Bit)",
        "tag": "IB",
        "core_question": "物理定律是信息处理的约束条件吗？",
        "why_now": "Landauer 原理 + 黑洞热力学 + 量子信息 = 信息是基础物理量的证据在积累。因果图可以建模'信息→物理'的通道。",
        "key_variables": ["entropy", "energy", "information", "spacetime_curvature",
                          "quantum_amplitude", "landauer_bound"],
        "key_domains": ["thermodynamics", "quantum", "geometry"],
        "key_lenses": ["stability_structure", "arrow_of_time", "path_integral"],
        "difficulty": 4,
        "reward": 5,
        "open_problems": [
            "黑洞熵是否穷尽了内部信息？",
            "量子纠错码和 AdS/CFT 的联系",
            "信息是否比物质/能量更基本？",
        ],
    },
    {
        "id": "geometric_unity",
        "name": "几何统一纲领 (Wheeler 路线)",
        "tag": "GU",
        "core_question": "所有基本相互作用都是几何吗？",
        "why_now": "PhysCausal 已经验证 δS=0 是唯一生成根，下一步是检验几何是否能统一所有力。geometric_identity 透镜已就位。",
        "key_variables": ["gauge_field", "spacetime_curvature", "higher_d_metric",
                          "geodesic_path", "force", "charge"],
        "key_domains": ["geometry", "general_relativity", "electromagnetism"],
        "key_lenses": ["geometric_identity", "wheeler_frontier", "group_theory"],
        "difficulty": 5,
        "reward": 5,
        "open_problems": [
            "电磁力 = 额外维度的曲率？(Kaluza-Klein)",
            "强相互作用能否几何化？",
            "Wheeler 的'pre-geometry'到底是什么？",
        ],
    },
    {
        "id": "causal_discovery",
        "name": "因果发现方法论",
        "tag": "CD",
        "core_question": "如何从观测数据中可靠地推断因果结构？",
        "why_now": "PhysCausal 的 do-calculus + creative evolution 是因果发现的独特组合。适合扩展到复杂系统。",
        "key_variables": ["force", "temperature", "pressure", "density",
                          "flow_rate", "induced_emf", "frequency"],
        "key_domains": ["classical", "thermodynamics", "electromagnetism"],
        "key_lenses": ["least_action_ontology", "stability_structure"],
        "difficulty": 2,
        "reward": 3,
        "open_problems": [
            "非线性系统中的因果推断",
            "时间序列中的 Granger vs Pearl",
            "多尺度因果发现",
        ],
    },
    # ── PhysCausal 特有方向 ──
    {
        "id": "causal_unification",
        "name": "因果统一纲领 (PhysCausal 特有)",
        "tag": "CU",
        "core_question": "所有基本定律能否从唯一的因果生成原理 (δS=0) 推导出来？",
        "why_now": "PhysCausal 的核心使命。Convergence_geodesic_path 已经展示了因果汇聚的力量。继续沿这条线: 所有能量形式 → 同一生成根。",
        "key_variables": ["energy", "kinetic_energy", "entropy", "force",
                          "geodesic_path", "quantum_amplitude"],
        "key_domains": ["unification", "classical", "quantum", "geometry"],
        "key_lenses": ["action_root", "bootstrap", "stability_structure"],
        "difficulty": 4,
        "reward": 5,
        "open_problems": [
            "能否从 δS=0 推导熵增？",
            "量子场论的作用量是否是唯一可能的？",
            "所有守恒定律 = 对称性的必然推论？(Noether 已给方向)",
        ],
    },
    {
        "id": "cross_domain_bridges",
        "name": "跨域桥接 (PhysCausal 特有)",
        "tag": "CB",
        "core_question": "量子域和几何域之间的因果桥接存在吗？怎样存在？",
        "why_now": "当前因果图上有 5 条 QM↔GR 桥接。Convergence_geodesic_path 量子交叉验证已暴露缺失桥梁。这是最成熟的探索方向。",
        "key_variables": ["quantum_amplitude", "geodesic_path", "spacetime_curvature",
                          "entanglement", "phase", "collapse_probability"],
        "key_domains": ["quantum", "geometry", "unification"],
        "key_lenses": ["path_integral", "geometric_identity", "wheeler_frontier"],
        "difficulty": 3,
        "reward": 4,
        "open_problems": [
            "entanglement → spacetime_curvature 是双向的吗？(ER=EPR)",
            "phase → geodesic_path: 几何相位和引力几何的关系",
            "stationary_path 作为量子→经典桥梁的建模",
        ],
    },
    {
        "id": "knowledge_synthesis",
        "name": "知识手册编纂 (PhysCausal 特有)",
        "tag": "KS",
        "core_question": "如何把已知物理知识组织成一个自洽、可查询、可推理的网络？",
        "why_now": "PhysCausal 的语义聚类 + 粗粒化 + 层次抽象已经就位。当前手册 8 卷 ~64KB。下一步是自动发现知识空白并补全。",
        "key_variables": ["knowledge_gap", "semantic_cluster", "abstraction_level"],
        "key_domains": ["meta", "documentation"],
        "key_lenses": ["classification_by_symmetry", "group_theory"],
        "difficulty": 1,
        "reward": 3,
        "open_problems": [
            "自动检测知识手册的逻辑漏洞",
            "跨卷引用的一致性检查",
            "从手册中自动生成研究问题",
        ],
    },
]


# ── 聚焦状态持久化 ──

from data_paths import focus_path
_FOCUS_FILE = focus_path()


def get_current_focus() -> Optional[Dict]:
    """获取当前选中的研究方向"""
    try:
        with open(_FOCUS_FILE) as f:
            data = json.load(f)
        direction_id = data.get("direction", "")
        for d in RESEARCH_DIRECTIONS:
            if d["id"] == direction_id:
                return d
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return None


def set_focus(direction_id: str) -> Dict:
    """设置研究方向 (可按 id 或 tag)"""
    for d in RESEARCH_DIRECTIONS:
        if d["id"] == direction_id or d["tag"] == direction_id.upper():
            with open(_FOCUS_FILE, "w") as f:
                json.dump({"direction": d["id"], "name": d["name"]}, f)
            return {"success": True, "direction": d}
    return {"success": False, "reason": f"未知方向: {direction_id}"}


def focus_report() -> str:
    """生成研究方向列表 (菜单)"""
    lines = [
        "══════ 物理研究方向 ══════",
        "  选择一个方向，物理学家将聚焦探索。",
        "",
    ]

    # 当前聚焦
    current = get_current_focus()
    if current:
        lines.append(f"  ▶ 当前聚焦: {current['tag']} {current['name']}")
        lines.append(f"    核心问题: {current['core_question']}")
        lines.append("")

    # 分成两组
    physics_dirs = [d for d in RESEARCH_DIRECTIONS if d["difficulty"] >= 3]
    physcausal_dirs = [d for d in RESEARCH_DIRECTIONS if d["difficulty"] < 3 or d["id"] in
                       ("cross_domain_bridges", "knowledge_synthesis", "causal_unification")]

    lines.append("  ── 基础物理前沿 ──")
    for i, d in enumerate(physics_dirs):
        if d["id"] in ("cross_domain_bridges", "causal_unification"):
            continue
        focused = " ▶" if current and current["id"] == d["id"] else "  "
        stars = "★" * d["difficulty"] + "·" * (5 - d["difficulty"])
        lines.append(f"  [{d['tag']}] {d['name']}")
        lines.append(f"      {d['core_question']}")
        lines.append(f"      难度{stars}  |  关键变量: {', '.join(d['key_variables'][:4])}")
        lines.append("")

    lines.append("  ── PhysCausal 特有方向 ──")
    for i, d in enumerate(RESEARCH_DIRECTIONS):
        if d["id"] not in ("causal_unification", "cross_domain_bridges", "knowledge_synthesis"):
            continue
        focused = " ▶" if current and current["id"] == d["id"] else "  "
        stars = "★" * d["difficulty"] + "·" * (5 - d["difficulty"])
        lines.append(f"  [{d['tag']}] {d['name']}")
        lines.append(f"      {d['core_question']}")
        lines.append(f"      难度{stars}  |  关键变量: {', '.join(d['key_variables'][:4])}")
        lines.append("")

    lines.append("  使用: focus <tag>   例如: focus QG")
    lines.append("        focus none    取消聚焦")
    return "\n".join(lines)


def bias_by_focus() -> Dict:
    """
    如果当前有聚焦方向，返回偏置参数。

    用于在 innovation_engine / frontier / speculate 中
    给聚焦方向的变量更高的采样权重。
    """
    current = get_current_focus()
    if not current:
        return {"active": False}

    return {
        "active": True,
        "tag": current["tag"],
        "name": current["name"],
        "key_variables": current["key_variables"],
        "key_domains": current["key_domains"],
        "key_lenses": current["key_lenses"],
        "variable_weight_boost": 3.0,  # 聚焦变量在采样时权重×3
    }
