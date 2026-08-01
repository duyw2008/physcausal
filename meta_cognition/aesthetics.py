"""
诺特的审美引擎 — 对称即美

四条美学原则:
  1. 对称即美 — 守恒量、规范不变性、Noether对应
  2. 相变即美 — 从无序中涌现有序
  3. 结构即美 — 自组织、层次化、跨尺度
  4. 简单即美 — 最少假设、最短路径

评分范围: 0.0 ~ 1.0，组合进假说排序
"""

from __future__ import annotations
from typing import Dict, List
from collections import defaultdict


# ═══════════════════════════════════════════════
# 对称属性库 — 哪些变量承载对称性
# ═══════════════════════════════════════════════

SYMMETRY_VARIABLES = {
    # 守恒量 — Noether定理的直接产物
    "momentum": {"symmetry": "空间平移不变性", "group": "translation", "weight": 1.0},
    "energy": {"symmetry": "时间平移不变性", "group": "translation", "weight": 1.0},
    "charge": {"symmetry": "U(1)规范不变性", "group": "U(1)", "weight": 1.0},
    "conserved_charge": {"symmetry": "连续对称→守恒", "group": "Noether", "weight": 1.0},
    "angular_momentum": {"symmetry": "旋转不变性", "group": "SO(3)", "weight": 0.9},
    "spin_angular_momentum": {"symmetry": "洛伦兹不变性", "group": "SO(3,1)", "weight": 0.9},
    
    # 规范场 — 对称性的载体
    "gauge_field": {"symmetry": "规范协变性", "group": "gauge", "weight": 0.9},
    "em_field_strength": {"symmetry": "U(1)规范不变", "group": "U(1)", "weight": 0.8},
    "4d_metric": {"symmetry": "广义协变性", "group": "diffeomorphism", "weight": 1.0},
    "higher_d_metric": {"symmetry": "高维广义协变性", "group": "diffeomorphism", "weight": 0.8},
    
    # 标度对称 — 临界现象
    "order_parameter": {"symmetry": "自发对称破缺", "group": "SSB", "weight": 0.8},
    "phase": {"symmetry": "对称破缺产物", "group": "SSB", "weight": 0.7},
    "equilibrium_state": {"symmetry": "平衡态对称性", "group": "equilibrium", "weight": 0.5},
    
    # 几何对称 — Wheeler的"几何即物理"
    "spacetime_curvature": {"symmetry": "广义协变性", "group": "diffeomorphism", "weight": 1.0},
    "geodesic_path": {"symmetry": "测地线=最短路径", "group": "variational", "weight": 0.7},
    "schwarzschild_radius": {"symmetry": "球对称解", "group": "SO(3)", "weight": 0.6},
    "wormhole_geometry": {"symmetry": "ER桥的拓扑对称", "group": "topological", "weight": 0.7},
    
    # 量子对称
    "wave_function": {"symmetry": "全局相位不变→概率守恒", "group": "U(1)", "weight": 0.9},
    "entangled_state": {"symmetry": "EPR关联的对称性", "group": "entanglement", "weight": 0.8},
    "quantum_amplitude": {"symmetry": "路径积分不变性", "group": "variational", "weight": 0.8},
}

# 相变相关变量
PHASE_TRANSITION_VARIABLES = {
    "order_parameter": 1.0,
    "phase": 0.9,
    "symmetry_breaking": 0.9,
    "critical_temperature": 0.7,
    "broken_symmetry": 0.7,
    "spontaneous_symmetry_breaking": 0.9,
}

# 结构涌现变量
STRUCTURE_VARIABLES = {
    "entropy": 0.6,            # 熵增→结构 (Prigogine)
    "free_energy": 0.7,        # 自由能极小→有序
    "equilibrium_state": 0.5,
    "horizon_area": 0.8,       # 黑洞——熵最大的结构
    "self_organization": 0.9,
    "pattern_formation": 0.8,
}


# ═══════════════════════════════════════════════
# 评分函数
# ═══════════════════════════════════════════════

def symmetry_score(variable: str) -> float:
    """单变量的对称分"""
    if variable in SYMMETRY_VARIABLES:
        return SYMMETRY_VARIABLES[variable]["weight"]
    return 0.0


def phase_transition_score(variable: str) -> float:
    """单变量的相变分"""
    return PHASE_TRANSITION_VARIABLES.get(variable, 0.0)


def structure_score(variable: str) -> float:
    """单变量的结构涌现分"""
    return STRUCTURE_VARIABLES.get(variable, 0.0)


def simplicity_score(chain_length: int, chain_depth: int) -> float:
    """
    简单性评分 — 越短越美。
    理想深度 2-3 (直接但不过于平凡)
    """
    if chain_depth <= 1:
        return 0.2  # 太浅——平凡的相邻关系
    elif chain_depth == 2:
        return 1.0  # 两步——简洁有力
    elif chain_depth == 3:
        return 0.9
    elif chain_depth <= 5:
        return 0.6
    else:
        return max(0.1, 1.0 / chain_depth)


def chain_elegance(variables: List[str], depth: int) -> Dict:
    """
    因果链的总体审美评分。
    
    Returns:
        {symmetry, phase, structure, simplicity, total, insights}
    """
    sym = sum(symmetry_score(v) for v in variables) / max(len(variables), 1)
    ph = sum(phase_transition_score(v) for v in variables) / max(len(variables), 1)
    st = sum(structure_score(v) for v in variables) / max(len(variables), 1)
    sim = simplicity_score(len(variables), depth)

    # 如果有对称变量且链短 → 特别美
    has_symmetry = any(symmetry_score(v) > 0.7 for v in variables)
    bonus = 0.1 if (has_symmetry and depth <= 3) else 0.0

    total = (sym * 0.35 + ph * 0.2 + st * 0.2 + sim * 0.25) + bonus
    total = round(min(total, 1.0), 2)

    insights = []
    if sym > 0.5:
        sym_vars = [v for v in variables if symmetry_score(v) > 0.7]
        if sym_vars:
            insights.append(f"对称性: {sym_vars[0]} 承载 {SYMMETRY_VARIABLES.get(sym_vars[0], {}).get('symmetry','?')}")
    if ph > 0.5:
        insights.append("路径经相变——从无序中涌现有序")
    if st > 0.3:
        insights.append("熵增驱动结构形成")
    if sim > 0.8:
        insights.append(f"简洁({depth}步)——优雅的直接联系")

    return {
        "symmetry": round(sym, 2),
        "phase": round(ph, 2),
        "structure": round(st, 2),
        "simplicity": round(sim, 2),
        "total": total,
        "insights": insights,
    }


def aesthetics_score(var_a: str, var_b: str, 
                     chain_a_vars: List[str] = None, chain_b_vars: List[str] = None,
                     depth_a: int = 0, depth_b: int = 0) -> float:
    """
    一对变量的审美总分 — 用于假说排序。
    两边的美都算，取平均。
    """
    va = [var_a] + (chain_a_vars or [])
    vb = [var_b] + (chain_b_vars or [])
    
    ea = chain_elegance(va, max(depth_a, 1))
    eb = chain_elegance(vb, max(depth_b, 1))
    
    combined = (ea["total"] + eb["total"]) / 2
    
    # 跨对称群加分：如果两端承载不同对称群 → 统一了不同对称性
    groups_a = SYMMETRY_VARIABLES.get(var_a, {}).get("group", "")
    groups_b = SYMMETRY_VARIABLES.get(var_b, {}).get("group", "")
    if groups_a and groups_b and groups_a != groups_b:
        combined = min(combined + 0.15, 1.0)
    
    return round(combined, 2)


def aesthetics_report(variables: List[str]) -> str:
    """审美分析报告"""
    lines = ["══════ 审美分析 ══════"]
    
    sym_vars = [(v, symmetry_score(v)) for v in variables if symmetry_score(v) > 0]
    phase_vars = [(v, phase_transition_score(v)) for v in variables if phase_transition_score(v) > 0]
    struct_vars = [(v, structure_score(v)) for v in variables if structure_score(v) > 0]
    
    if sym_vars:
        lines.append(f"\n  对称性 ({len(sym_vars)}):")
        for v, s in sorted(sym_vars, key=lambda x: -x[1])[:5]:
            info = SYMMETRY_VARIABLES.get(v, {})
            lines.append(f"    {v}: {info.get('symmetry','?')} ({info.get('group','?')})")
    
    if phase_vars:
        lines.append(f"\n  相变 ({len(phase_vars)}):")
        for v, _ in sorted(phase_vars, key=lambda x: -x[1])[:3]:
            lines.append(f"    {v}")
    
    if struct_vars:
        lines.append(f"\n  结构涌现 ({len(struct_vars)}):")
        for v, _ in sorted(struct_vars, key=lambda x: -x[1])[:3]:
            lines.append(f"    {v}")
    
    return "\n".join(lines)
