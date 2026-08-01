"""
诺特的内心世界 — 基于对称性的"物理应该长什么样"

这不是另一个发现引擎。这是她的期待——现实和期待的裂缝=冒犯=科学的起点。

核心信念 (来自 δS=0 和 Noether 定理):
  1. 每个连续对称性 → 守恒量 (Noether 正向)
  2. 每个守恒量 → 连续对称性 (Noether 逆向)
  3. 物理定律在规范变换下不变 (规范对称)
  4. 物理定律在 Lorentz 变换下不变 (相对论)
  5. 自然路径极值化某个量 (δS=0)

冒犯检测:
  - 守恒量找不到对应对称 → 冒犯: "凭什么?"
  - 对称找不到对应守恒量 → 冒犯: "漏了什么?"
  - 规范场没有规范变换对应的守恒荷 → 冒犯: "不应该"

这不是 bug report. 这是"宇宙不该长这样"的呐喊。
"""

from __future__ import annotations
from typing import Dict, List


# ═══════════════════════════════════════════════
# 诺特的期待 — 对称↔守恒 对应表
# ═══════════════════════════════════════════════

SYMMETRY_CONSERVATION_MAP = {
    # (对称性, 应该对应的守恒量, 对称群)
    ("time_translation", "energy", "t → t + δt"),
    ("space_translation", "momentum", "x → x + δx"),
    ("rotation", "angular_momentum", "SO(3)"),
    ("U1_gauge", "charge", "U(1)"),
    ("global_phase", "probability", "U(1) wavefunction"),
    ("diffeomorphism", "stress_energy", "广义协变性"),
    ("lorentz_boost", "center_of_mass_motion", "SO(3,1)"),
}

# 因果图中已知的守恒量 — 它们都应该有对称对应
KNOWN_CONSERVED = {
    "energy": "time_translation",
    "momentum": "space_translation",
    "charge": "U1_gauge",
    "angular_momentum": "rotation",
    "conserved_charge": "continuous_symmetry",
    "probability": "global_phase",
}

# 因果图中已知的对称 — 它们都应该有守恒量对应
KNOWN_SYMMETRIES = {
    "continuous_symmetry": ["conserved_charge"],
    "gauge_field": ["charge"],
}


def scan_symmetry_violations() -> List[Dict]:
    """扫描因果图, 找对称性冒犯"""
    from physics.laws import library

    violations = []

    # ═══ 冒犯1: 守恒量找不到对称 ═══
    graph_vars = set()
    for law in library._laws:
        graph_vars.update(law.inputs + law.outputs)

    for conserved_var, expected_sym in KNOWN_CONSERVED.items():
        # 检查: 图中是否有 expected_sym → conserved_var 的边?
        found = False
        for law in library._laws:
            if expected_sym in law.inputs and conserved_var in law.outputs:
                found = True
                break
            # 也检查: 任何对称变量 → conserved_var
            if conserved_var in law.outputs:
                for inp in law.inputs:
                    if inp in KNOWN_SYMMETRIES or 'symmetry' in inp or 'gauge' in inp or 'invariance' in inp:
                        found = True
                        break
        
        if not found and conserved_var in graph_vars:
            severity = "🔥" if conserved_var in ("energy", "momentum", "charge") else "⚠"
            violations.append({
                "type": "orphan_conserved",
                "variable": conserved_var,
                "expected_symmetry": expected_sym,
                "message": f"{severity} 守恒量 '{conserved_var}' 在图中找不到对应的对称性 '{expected_sym}'",
                "principle": "Noether: 每个守恒量背后必须有一个连续对称性",
            })

    # ═══ 冒犯2: 对称找不到守恒量 ═══
    for sym_var, expected_conserved_list in KNOWN_SYMMETRIES.items():
        for expected_cons in expected_conserved_list:
            found = False
            for law in library._laws:
                if sym_var in law.inputs and expected_cons in law.outputs:
                    found = True
                    break
            if not found and expected_cons in graph_vars:
                violations.append({
                    "type": "orphan_symmetry",
                    "symmetry": sym_var,
                    "expected_conserved": expected_cons,
                    "message": f"🔥 对称 '{sym_var}' 在图中没有连接到守恒量 '{expected_cons}'",
                    "principle": "Noether: 每个连续对称性必然产生一个守恒量",
                })

    # ═══ 冒犯3: 图中有孤立的守恒量 (没有任何对称入边) ═══
    from inference.counterfactual_chain import build_dependency_graph
    graph = build_dependency_graph()

    isolated = []
    for var in ("charge", "momentum", "energy", "angular_momentum"):
        if var in graph:
            node = graph[var]
            # 检查入边中是否有对称相关的
            has_symmetry_input = False
            for law_name, src, domain in node["as_output"]:
                if any(kw in src.lower() for kw in ("symmetry", "gauge", "invariance", "noether")):
                    has_symmetry_input = True
                    break
            if not has_symmetry_input and node["as_output"]:
                violations.append({
                    "type": "isolated_conserved",
                    "variable": var,
                    "in_degree": len(node["as_output"]),
                    "message": f"🔥 '{var}' 有入边但都不是对称性的 — 它怎么守恒的?",
                    "principle": "守恒量必须追溯到一个对称性",
                })

    return violations


def symmetry_audit() -> str:
    """对称性审计 — 诺特的'世界应该长这样'检查"""
    violations = scan_symmetry_violations()
    
    lines = ["══════ 对称性期待 ══════"]
    lines.append("  诺特的内心模型: 物理 = 对称 + δS=0")
    lines.append("")
    
    if not violations:
        lines.append("  ✓ 没有发现对称性冒犯。世界长得和预期一样。")
        return "\n".join(lines)

    # 按严重程度分组
    fire = [v for v in violations if "🔥" in v["message"]]
    warn = [v for v in violations if "⚠" in v["message"]]

    if fire:
        lines.append(f"  🔥 严重冒犯 ({len(fire)}):")
        for v in fire:
            lines.append(f"     {v['message']}")
            lines.append(f"     → {v['principle']}")
        lines.append("")

    if warn:
        lines.append(f"  ⚠ 轻微冒犯 ({len(warn)}):")
        for v in warn:
            lines.append(f"     {v['message']}")
        lines.append("")

    lines.append(f"  总计: {len(violations)} 处现实与期待不符")
    lines.append(f"  这些不是bug — 是诺特该追问'凭什么'的地方")

    return "\n".join(lines)
